
import chromadb
from sentence_transformers import SentenceTransformer

print("Loading embedding model...")

model = SentenceTransformer("all-MiniLM-L6-v2")

client = chromadb.PersistentClient(path="./vectorstore")

text_collection = client.get_collection("documents")
table_collection = client.get_collection("tables")
image_collection = client.get_collection("images")


def retrieve_context(question):

    query_embedding = model.encode(question).tolist()

    context_parts = []
    sources = []

    collections = [
        ("text", text_collection, 5),
        ("table", table_collection, 5),
        ("image", image_collection, 3)
    ]

    for source_type, collection, top_k in collections:

        count = collection.count()

        if count == 0:
            continue

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, count),
            include=["documents", "metadatas", "distances"]
        )

        for doc, metadata in zip(
            results["documents"][0],
            results["metadatas"][0]
        ):

            if not doc or not metadata:
                continue

            source = metadata.get("source", "Unknown")
            page = metadata.get("page", "Unknown")

            context_parts.append(
                f"Source type: {source_type}\n"
                f"PDF: {source}\n"
                f"Page: {page}\n"
                f"Content: {doc}"
            )

            sources.append({
                "type": source_type,
                "source": source,
                "page": page
            })

    return "\n\n".join(context_parts), sources
