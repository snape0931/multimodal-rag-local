
import chromadb
import ollama
from sentence_transformers import SentenceTransformer

# 1. Load embedding model
print("Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

# 2. Connect to ChromaDB
client = chromadb.PersistentClient(path="./vectorstore")

text_collection = client.get_collection(name="documents")
table_collection = client.get_collection(name="tables")

print("Connected to database!")
print("Text chunks:", text_collection.count())
print("Table records:", table_collection.count())

# 3. Ask question
query = input("\nAsk a question: ")

query_embedding = model.encode(query).tolist()

# 4. Retrieve relevant text chunks
text_results = text_collection.query(
    query_embeddings=[query_embedding],
    n_results=min(3, text_collection.count())
)

# 5. Retrieve relevant table records
table_results = table_collection.query(
    query_embeddings=[query_embedding],
    n_results=min(3, table_collection.count())
)

# 6. Combine retrieved context
context_parts = []

for doc in text_results["documents"][0]:
    context_parts.append("PDF TEXT:\n" + doc)

for table in table_results["documents"][0]:
    context_parts.append("PDF TABLE:\n" + table)

context = "\n\n".join(context_parts)

# 7. Generate answer using Llama
prompt = f"""
You are a helpful document assistant.

Answer the question using the provided PDF text
and table information.

Use numerical values from tables accurately.
If the answer is unavailable in the context,
say that the documents do not contain this information.

Context:
{context}

Question:
{query}

Answer:
"""

print("\nGenerating answer...")

response = ollama.chat(
    model="llama3.2:3b",
    messages=[
        {"role": "user", "content": prompt}
    ]
)

# 8. Display final answer
print("\n========== FINAL ANSWER ==========\n")
print(response["message"]["content"])
