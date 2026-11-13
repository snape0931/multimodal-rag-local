from pathlib import Path

import pymupdf

from backend.retrieval import model, text_collection

CHUNK_SIZE = 800      # characters per chunk
CHUNK_OVERLAP = 150   # characters shared between neighbouring chunks


def split_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Split text into overlapping chunks, breaking at spaces."""

    text = " ".join(text.split())
    chunks = []
    start = 0
    length = len(text)

    while start < length:
        end = min(start + chunk_size, length)

        if end < length:
            cut = text.rfind(" ", start + chunk_size // 2, end)
            if cut != -1:
                end = cut

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= length:
            break

        start = max(end - overlap, start + 1)

    return chunks


def ingest_pdf_text(pdf_path):

    pdf_path = Path(pdf_path)
    source = pdf_path.name

    print(f"Processing PDF: {source}")

    # Remove old records so re-uploading the same PDF doesn't duplicate chunks
    try:
        text_collection.delete(where={"source": source})
    except Exception:
        pass

    documents = []
    metadatas = []
    ids = []

    pdf = pymupdf.open(str(pdf_path))

    try:
        for page_number, page in enumerate(pdf, start=1):

            text = page.get_text("text")

            if not text or not text.strip():
                continue

            for chunk_number, chunk in enumerate(split_text(text)):
                documents.append(chunk)
                metadatas.append({
                    "source": source,
                    "page": page_number,
                    "type": "text"
                })
                ids.append(f"{source}_p{page_number}_c{chunk_number}")
    finally:
        pdf.close()

    if not documents:
        print("No extractable text found (is this a scanned PDF?)")
        return {
            "status": "completed",
            "chunks_indexed": 0
        }

    print(f"Generating embeddings for {len(documents)} chunks...")

    embeddings = model.encode(
        documents,
        batch_size=64,
        show_progress_bar=False
    ).tolist()

    text_collection.upsert(
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids
    )

    print(f"Successfully indexed {source}")

    return {
        "status": "completed",
        "chunks_indexed": len(documents)
    }