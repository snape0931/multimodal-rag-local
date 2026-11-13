
from pathlib import Path
from pypdf import PdfReader

# Reuse the embedding model and ChromaDB collection
# already loaded by backend.retrieval
from backend.retrieval import model, text_collection


def split_text(text, chunk_size=500, overlap=100):
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start += chunk_size - overlap

    return chunks


def ingest_pdf_text(pdf_path):

    pdf_path = Path(pdf_path)
    filename = pdf_path.name

    print(f"Processing PDF: {filename}")

    reader = PdfReader(str(pdf_path))

    all_chunks = []
    all_metadata = []
    all_ids = []

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

    if not all_chunks:
        return {
            "status": "completed",
            "filename": filename,
            "chunks_added": 0,
            "message": "No extractable text found."
        }

    print(f"Generating embeddings for {len(all_chunks)} chunks...")

    embeddings = model.encode(
        all_chunks,
        show_progress_bar=False
    ).tolist()

    # Upsert updates existing IDs instead of creating duplicates
    text_collection.upsert(
        documents=all_chunks,
        embeddings=embeddings,
        metadatas=all_metadata,
        ids=all_ids
    )

    print(f"Successfully indexed {filename}")

    return {
        "status": "completed",
        "filename": filename,
        "chunks_added": len(all_chunks)
    }
