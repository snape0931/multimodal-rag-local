from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from pathlib import Path

from backend.retrieval import (
    retrieve_context,
    text_collection,
    table_collection,
    image_collection
)
from backend.generation import generate_answer
from backend.ingestion import ingest_pdf_text
from backend.table_ingestion import ingest_pdf_tables
from backend.image_ingestion import ingest_pdf_images


app = FastAPI(
    title="Multimodal RAG API",
    description="Local PDF question-answering system",
    version="2.3"
)

UPLOAD_DIR = Path("data/documents")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class QuestionRequest(BaseModel):
    question: str
    document: str | None = None

@app.get("/")
def home():
    return {"message": "Multimodal RAG API is running!"}


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "text_chunks": 110,
        "message": "API is running"
    }


def run_image_ingestion(file_path: Path):
    """Runs after the upload response is sent, so slow image
    descriptions don't block or time out the request."""
    try:
        result = ingest_pdf_images(file_path)
        print(f"Image ingestion finished for {file_path.name}: {result}")
    except Exception as e:
        print(f"Image ingestion failed for {file_path.name}: {e}")


@app.get("/documents")
def list_documents():

    try:
        documents = [
            {
                "filename": file.name,
                "size_kb": round(file.stat().st_size / 1024, 2)
            }
            for file in UPLOAD_DIR.iterdir()
            if file.is_file() and file.suffix.lower() == ".pdf"
        ]

        return {
            "total_documents": len(documents),
            "documents": documents
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Could not retrieve documents: {str(e)}"
        )

@app.delete("/documents/{filename}")
def delete_document(filename: str):

    # Prevent directory traversal
    if Path(filename).name != filename or not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Invalid PDF filename."
        )

    file_path = UPLOAD_DIR / filename

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    try:
        # Delete indexed records from all collections
        text_collection.delete(where={"source": filename})
        table_collection.delete(where={"source": filename})
        image_collection.delete(where={"source": filename})

        # Delete the original PDF
        file_path.unlink()

        return {
            "message": "Document and indexed data deleted successfully.",
            "filename": filename
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Document deletion failed: {str(e)}"
        )

@app.post("/upload")
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed."
        )

    filename = Path(file.filename).name
    file_path = UPLOAD_DIR / filename

    try:
        content = await file.read()

        if not content.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=400,
                detail="Invalid PDF file."
            )

        file_path.write_bytes(content)

        # 1. Extract and index text (fast, runs now)
        text_result = ingest_pdf_text(file_path)

        # 2. Extract and index tables (fast, runs now)
        table_result = ingest_pdf_tables(file_path)

        # 3. Extract and index images (slow, runs in the background)
        background_tasks.add_task(run_image_ingestion, file_path)

        return {
            "message": "Text and tables indexed. Images are processing in the background.",
            "filename": filename,
            "text_ingestion": text_result,
            "table_ingestion": table_result,
            "image_ingestion": "running in background"
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Upload or ingestion failed: {str(e)}"
        )

    finally:
        await file.close()


@app.post("/ask")
def ask_question(request: QuestionRequest):

    query = request.question.strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    try:
        context, sources = retrieve_context(
    query,
    document=request.document
)

        if not context:
            raise HTTPException(
                status_code=404,
                detail="No relevant information found."
            )

        answer = generate_answer(query, context)

        unique_sources = []
        seen = set()

        for source in sources:
            key = (
                source["type"],
                source["source"],
                source["page"]
            )

            if key not in seen:
                seen.add(key)
                unique_sources.append(source)

        return {
            "question": query,
            "answer": answer,
            "sources": unique_sources
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Answer generation failed: {str(e)}"
        )