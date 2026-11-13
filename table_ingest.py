
import os
import json
import chromadb
from sentence_transformers import SentenceTransformer

# Load embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Connect to ChromaDB
client = chromadb.PersistentClient(path="./vectorstore")

# Create a separate collection for tables
try:
    client.delete_collection(name="tables")
except Exception:
    pass

collection = client.create_collection(name="tables")

TABLE_FOLDER = "data/extracted_tables"

documents = []
metadatas = []
ids = []

# Read all extracted JSON files
for filename in os.listdir(TABLE_FOLDER):
    if filename.endswith(".json"):
        file_path = os.path.join(TABLE_FOLDER, filename)

        with open(file_path, "r", encoding="utf-8") as f:
            tables = json.load(f)

        source_pdf = filename.replace("_tables.json", ".pdf")

        for index, table in enumerate(tables):
            table_text = f"Source: {source_pdf}\n"
            table_text += f"Page: {table['page']}\n"
            table_text += f"Table: {table['table_number']}\n"

            for column, value in table["data"].items():
                table_text += f"{column}: {value}\n"

            documents.append(table_text)
            metadatas.append({
                "source": source_pdf,
                "page": table["page"],
                "type": "table"
            })
            ids.append(f"{source_pdf}_table_{index}")

# Generate embeddings and store
if documents:
    embeddings = model.encode(documents).tolist()

    collection.add(
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids
    )

print("Tables successfully stored in ChromaDB!")
print("Total table records:", collection.count())
