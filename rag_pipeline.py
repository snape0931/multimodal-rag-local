
import chromadb
import ollama
from sentence_transformers import SentenceTransformer

print("Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

client = chromadb.PersistentClient(path="./vectorstore")

# Connect to all three collections
text_collection = client.get_collection("documents")
table_collection = client.get_collection("tables")
image_collection = client.get_collection("images")

print("\nConnected to ChromaDB!")
print("Text chunks:", text_collection.count())
print("Table records:", table_collection.count())
print("Image descriptions:", image_collection.count())

query = input("\nAsk your question: ")

query_embedding = model.encode(query).tolist()

context_parts = []

# Retrieve relevant text
text_results = text_collection.query(
    query_embeddings=[query_embedding],
    n_results=min(3, text_collection.count())
)

# Retrieve relevant tables
table_results = table_collection.query(
    query_embeddings=[query_embedding],
    n_results=min(3, table_collection.count())
)

# Retrieve relevant images
image_results = image_collection.query(
    query_embeddings=[query_embedding],
    n_results=min(3, image_collection.count())
)

# Combine retrieved information
for doc, metadata in zip(
    text_results["documents"][0],
    text_results["metadatas"][0]
):
    context_parts.append(
        f"PDF TEXT | Source: {metadata['source']} "
        f"| Page: {metadata['page']}\n{doc}"
    )

for doc, metadata in zip(
    table_results["documents"][0],
    table_results["metadatas"][0]
):
    context_parts.append(
        f"PDF TABLE | Source: {metadata['source']} "
        f"| Page: {metadata['page']}\n{doc}"
    )

for doc, metadata in zip(
    image_results["documents"][0],
    image_results["metadatas"][0]
):
    context_parts.append(
        f"PDF IMAGE | Source: {metadata['source']} "
        f"| Page: {metadata['page']}\n{doc}"
    )

context = "\n\n".join(context_parts)

prompt = f"""
You are a multimodal PDF research assistant.

Answer the user's question using the retrieved
text, tables and image descriptions.

Rules:
- Use numerical values accurately.
- Combine information from different sources when relevant.
- Do not invent facts.
- Mention the source PDF and page number.
- If information is unavailable, say so.

Retrieved Context:
{context}

Question:
{query}

Answer:
"""

print("\nGenerating answer using Llama...")

response = ollama.chat(
    model="llama3.2:3b",
    messages=[
        {"role": "user", "content": prompt}
    ]
)

print("\n========== FINAL ANSWER ==========\n")
print(response["message"]["content"])
