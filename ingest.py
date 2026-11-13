
import os
import chromadb
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

# 1. Load embedding model
print("Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

# 2. Connect to ChromaDB
client = chromadb.PersistentClient(path="./vectorstore")

# Rebuild collection to avoid duplicate or stale chunks
try:
    client.delete_collection(name="documents")
except Exception:
    pass

collection = client.create_collection(name="documents")

# 3. Folder containing PDFs
pdf_folder = "data/documents"

pdf_files = [
    os.path.join(pdf_folder, file)
    for file in os.listdir(pdf_folder)
    if file.lower().endswith(".pdf")
]

if not pdf_files:
    print("No PDF files found!")
    exit()

print(f"Found {len(pdf_files)} PDF files.")

# 4. Text chunking function
def split_text(text, chunk_size=500, overlap=100):
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap

    return chunks


all_chunks = []
all_metadata = []
all_ids = []

# 5. Process every PDF
for pdf_path in pdf_files:

    filename = os.path.basename(pdf_path)
    print(f"\nProcessing: {filename}")

    reader = PdfReader(pdf_path)

    for page_num, page in enumerate(reader.pages, start=1):

        text = page.extract_text()

        if not text or not text.strip():
            continue

        chunks = split_text(text)

        for chunk_num, chunk in enumerate(chunks):

            all_chunks.append(chunk)

            all_metadata.append({
                "source": filename,
                "page": page_num
            })

            all_ids.append(
                f"{filename}_page_{page_num}_chunk_{chunk_num}"
            )

    print(f"Finished processing {filename}")

# 6. Generate embeddings and store
if not all_chunks:
    print("No extractable text found in the PDFs.")
    exit()

print("\nGenerating embeddings...")

embeddings = model.encode(
    all_chunks,
    show_progress_bar=True
).tolist()

collection.add(
    documents=all_chunks,
    embeddings=embeddings,
    metadatas=all_metadata,
    ids=all_ids
)

print("\nAll PDFs successfully stored!")
print(f"Total PDFs processed: {len(pdf_files)}")
print(f"Total chunks stored: {collection.count()}")
