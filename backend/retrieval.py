
import chromadb
from sentence_transformers import SentenceTransformer, CrossEncoder

print("Loading embedding model...")

# 1. Embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# 2. Cross-encoder reranking model
print("Loading reranking model...")

reranker = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)

# 3. Connect to ChromaDB
client = chromadb.PersistentClient(path="./vectorstore")

text_collection = client.get_collection("documents")
table_collection = client.get_collection("tables")
image_collection = client.get_collection("images")


def retrieve_context(question, document=None):

    # 4. Generate query embedding
    query_embedding = model.encode(question).tolist()

    candidates = []

    # 5. Retrieve candidates from all three collections
    collections = [
        ("text", text_collection, 10),
        ("table", table_collection, 10),
        ("image", image_collection, 5)
    ]

    for source_type, collection, top_k in collections:

        count = collection.count()

        if count == 0:
            continue

        query_args = {
            "query_embeddings": [query_embedding],
            "n_results": min(top_k, count),
            "include": ["documents", "metadatas", "distances"]
        }

        # Filter by PDF filename if specified
        if document:
            query_args["where"] = {"source": document}

        results = collection.query(**query_args)

        for doc, metadata, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        ):

            if not doc or not metadata:
                continue

            candidates.append({
                "type": source_type,
                "content": doc,
                "source": metadata.get("source", "Unknown"),
                "page": metadata.get("page", "Unknown"),
                "distance": distance
            })

    if not candidates:
        return "", []

    # 6. Rerank candidates using cross-encoder
    pairs = [
        (question, candidate["content"])
        for candidate in candidates
    ]

    scores = reranker.predict(pairs)

    for candidate, score in zip(candidates, scores):
        candidate["rerank_score"] = float(score)

    # 7. Sort by relevance score
    candidates.sort(
        key=lambda x: x["rerank_score"],
        reverse=True
    )

    # 8. Remove weakly relevant results
    MIN_RELEVANCE_SCORE = 0.0

    candidates = [
        item for item in candidates
        if item["rerank_score"] >= MIN_RELEVANCE_SCORE
    ]

    if not candidates:
        return "", []

    # 9. Remove exact duplicate results
    unique_candidates = []
    seen = set()

    for item in candidates:

        key = (
            item["type"],
            item["source"],
            item["page"],
            item["content"]
        )

        if key not in seen:
            seen.add(key)
            unique_candidates.append(item)

    # 10. Keep the top 10 unique results
    selected = unique_candidates[:10]

    context_parts = []
    sources = []

    # 11. Prepare context and source metadata
    for item in selected:

        context_parts.append(
            f"Source type: {item['type']}\n"
            f"PDF: {item['source']}\n"
            f"Page: {item['page']}\n"
            f"Content: {item['content']}"
        )

        sources.append({
            "type": item["type"],
            "source": item["source"],
            "page": item["page"]
        })

    return "\n\n".join(context_parts), sources
