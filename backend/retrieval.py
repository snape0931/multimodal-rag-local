import chromadb
from sentence_transformers import SentenceTransformer, CrossEncoder

# Chunks scoring below MIN_SCORE are treated as irrelevant. If nothing passes,
# the API replies "not found" without even calling the language model.
# ms-marco scores are logits: relevant is usually above 0, unrelated is very negative.
MIN_SCORE = -4.0
TOP_K_FINAL = 4          # chunks sent to the language model (fewer = faster)
DEBUG_SCORES = True

print("Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

print("Loading reranking model...")
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

client = chromadb.PersistentClient(path="./vectorstore")

text_collection = client.get_or_create_collection("documents")
table_collection = client.get_or_create_collection("tables")
image_collection = client.get_or_create_collection("images")


def warm_up_retrieval():
    """Run the models once at startup so the first question isn't slow."""
    try:
        model.encode("warm up")
        reranker.predict([("warm up", "warm up")])
        print("Retrieval models warmed up.")
    except Exception as e:
        print(f"Retrieval warm-up skipped: {e}")


def retrieve_context(question, document=None):

    query_embedding = model.encode(question).tolist()
    where = {"source": document} if document else None

    candidates = []

    collections = [
        ("text", text_collection, 6),
        ("table", table_collection, 4),
        ("image", image_collection, 3),
    ]

    for source_type, collection, top_k in collections:

        count = collection.count()
        if count == 0:
            continue

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, count),
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        for doc, metadata, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            if not doc or not metadata:
                continue

            candidates.append({
                "type": source_type,
                "content": doc,
                "source": metadata.get("source", "Unknown"),
                "page": metadata.get("page", "Unknown"),
                "distance": distance,
            })

    if not candidates:
        return "", []

    # Rerank with the cross-encoder
    pairs = [(question, c["content"]) for c in candidates]
    scores = reranker.predict(pairs)

    for c, s in zip(candidates, scores):
        c["rerank_score"] = float(s)

    candidates.sort(key=lambda x: x["rerank_score"], reverse=True)

    if DEBUG_SCORES:
        top = [round(c["rerank_score"], 2) for c in candidates[:5]]
        print(f"Top rerank scores: {top} (cutoff {MIN_SCORE})")

    # Drop irrelevant chunks
    candidates = [c for c in candidates if c["rerank_score"] > MIN_SCORE]

    if not candidates:
        return "", []

    selected = candidates[:TOP_K_FINAL]

    context_parts = []
    sources = []

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
            "page": item["page"],
        })

    return "\n\n".join(context_parts), sources