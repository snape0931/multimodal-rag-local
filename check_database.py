
import chromadb

client = chromadb.PersistentClient(path="./vectorstore")

for name in ["documents", "tables", "images"]:
    try:
        collection = client.get_collection(name=name)

        print(f"\n{name.upper()}")
        print("Total records:", collection.count())

        results = collection.get(
    include=["metadatas"]
     )

        sources = set(
            metadata.get("source", "Unknown")
            for metadata in results["metadatas"]
        )

        print("PDF sources:", sources)

    except Exception as e:
        print(name, "Error:", e)
