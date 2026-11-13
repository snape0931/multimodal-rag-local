import json
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.retrieval import (
    retrieve_context,
    warm_up_retrieval,
    text_collection,
    table_collection,
    image_collection
)
from backend.generation import (
    generate_answer,
    stream_answer,
    small_talk_reply,
    build_search_query,
    sample_pdf_text,
    generate_summary,
    warm_up as warm_up_llm,
    NOT_FOUND_MESSAGE
)
from backend.ingestion import ingest_pdf_text
from backend.table_ingestion import ingest_pdf_tables
from backend.image_ingestion import ingest_pdf_images


def warm_up_everything():
    warm_up_retrieval()
    warm_up_llm()


@asynccontextmanager
async def lifespan(app):
    # Load models in the background so startup isn't delayed
    threading.Thread(target=warm_up_everything, daemon=True).start()
    yield


app = FastAPI(
    title="Multimodal RAG API",
    description="Local PDF question-answering system",
    version="3.2",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8001",
        "http://127.0.0.1:8001"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

UPLOAD_DIR = Path("data/documents")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ---------- saved summaries (survive restarts) ----------

SUMMARY_FILE = Path("data/summaries.json")
summaries_lock = threading.Lock()


def load_summaries():
    try:
        if SUMMARY_FILE.exists():
            return json.loads(SUMMARY_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Could not read summaries: {e}")
    return {}


summaries = load_summaries()


def save_summaries():
    try:
        with summaries_lock:
            SUMMARY_FILE.parent.mkdir(parents=True, exist_ok=True)
            SUMMARY_FILE.write_text(
                json.dumps(summaries, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
    except Exception as e:
        print(f"Could not save summaries: {e}")


# ---------- background processing state ----------

STAGE_LABELS = {
    "queued": "⏳ Waiting in line...",
    "text": "📖 Reading the text...",
    "tables": "📊 Finding tables...",
    "summary": "✨ Writing a quick summary...",
    "images": "🖼️ Describing images...",
    "done": "✅ All done",
    "error": "❌ Something went wrong",
}

# While in these stages the summary may still be on its way
SUMMARY_PENDING_STAGES = {"queued", "text", "tables", "summary"}

processing_status = {}
processing_lock = threading.Lock()   # index one PDF at a time


def set_status(filename, stage, error=None):
    warnings = (
        []
        if stage == "queued"
        else processing_status.get(filename, {}).get("warnings", [])
    )
    processing_status[filename] = {
        "stage": stage,
        "error": error,
        "warnings": warnings
    }


def add_warning(filename, text):
    entry = processing_status.setdefault(
        filename, {"stage": "queued", "error": None, "warnings": []}
    )
    entry["warnings"].append(text)


def process_pdf(file_path: Path):
    """Runs in the background: text, tables, summary, then images."""

    name = file_path.name

    with processing_lock:
        total = perf_counter()

        # 1. Text first: it answers most questions
        set_status(name, "text")
        t = perf_counter()
        try:
            ingest_pdf_text(file_path)
            print(f"text ingestion: {perf_counter() - t:.1f}s")
        except Exception as e:
            print(f"Text ingestion failed for {name}: {e}")
            set_status(name, "error", error=f"Reading the text failed: {e}")
            return

        # 2. Tables
        set_status(name, "tables")
        t = perf_counter()
        try:
            ingest_pdf_tables(file_path)
            print(f"table ingestion: {perf_counter() - t:.1f}s")
        except Exception as e:
            print(f"Table ingestion failed for {name}: {e}")
            add_warning(name, "tables skipped")

        # 3. Summary + suggested questions (uses the already-loaded answer model)
        set_status(name, "summary")
        t = perf_counter()
        try:
            sample = sample_pdf_text(file_path)
            result = generate_summary(sample) if sample else None

            if result:
                summaries[name] = result
                save_summaries()

            print(f"summary: {perf_counter() - t:.1f}s")
        except Exception as e:
            print(f"Summary skipped for {name}: {e}")

        # 4. Images (slowest)
        set_status(name, "images")
        t = perf_counter()
        try:
            result = ingest_pdf_images(file_path)
            print(f"image ingestion: {perf_counter() - t:.1f}s {result}")
        except Exception as e:
            print(f"Image ingestion failed for {name}: {e}")
            add_warning(name, "images skipped (is Ollama running?)")

        set_status(name, "done")
        print(f"All done for {name} in {perf_counter() - total:.0f}s")


def unique_sources(sources):
    result = []
    seen = set()

    for source in sources:
        key = (source["type"], source["source"], source["page"])

        if key not in seen:
            seen.add(key)
            result.append(source)

    return result


# ---------- models ----------

class ChatTurn(BaseModel):
    role: str
    content: str


class QuestionRequest(BaseModel):
    question: str
    document: str | None = None
    history: list[ChatTurn] = []


# ---------- routes ----------

@app.get("/")
def home():
    return {"message": "Multimodal RAG API is running!"}


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "text_chunks": text_collection.count(),
        "table_chunks": table_collection.count(),
        "image_descriptions": image_collection.count()
    }


@app.get("/documents")
def list_documents():
    try:
        documents = [
            {
                "filename": file.name,
                "size_kb": round(file.stat().st_size / 1024, 2),
                "status": processing_status.get(file.name, {}).get("stage", "done")
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


@app.get("/status/{filename}")
def get_status(filename: str):

    safe_name = Path(filename).name
    info = processing_status.get(safe_name)

    if info is None:
        # Not tracked (e.g. after a restart): treat as ready if the file exists
        if (UPLOAD_DIR / safe_name).exists():
            return {
                "stage": "done",
                "label": STAGE_LABELS["done"],
                "error": None,
                "warnings": []
            }
        raise HTTPException(status_code=404, detail="Document not found.")

    return {**info, "label": STAGE_LABELS.get(info["stage"], "")}


@app.get("/summary/{filename}")
def get_summary(filename: str):
    """Summary and suggested questions for a document, once they are ready."""

    safe_name = Path(filename).name
    data = summaries.get(safe_name)

    if data:
        return {"ready": True, **data}

    stage = processing_status.get(safe_name, {}).get("stage")

    return {
        "ready": False,
        # finished = no summary is coming (it failed, or was never requested)
        "finished": stage not in SUMMARY_PENDING_STAGES
    }


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
        processing_status.pop(filename, None)

        if summaries.pop(filename, None) is not None:
            save_summaries()

        # Delete extracted images for this PDF
        for image_file in Path("data/extracted_images").glob(
            f"{file_path.stem}_page*"
        ):
            image_file.unlink()

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
    """Saves the PDF and returns immediately. Indexing continues in the
    background; poll /status/{filename} for progress."""

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

        # A re-upload replaces the old summary
        if summaries.pop(filename, None) is not None:
            save_summaries()

        set_status(filename, "queued")
        background_tasks.add_task(process_pdf, file_path)

        return {
            "message": "PDF uploaded. Indexing has started in the background.",
            "filename": filename,
            "file_size_mb": round(len(content) / (1024 * 1024), 2),
            "status": "queued"
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )

    finally:
        await file.close()


@app.post("/ask")
def ask_question(request: QuestionRequest):
    """Non-streaming answer (useful for testing in /docs)."""

    query = request.question.strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    try:
        reply = small_talk_reply(query)

        if reply:
            return {"question": query, "answer": reply, "sources": []}

        history = [turn.model_dump() for turn in request.history]
        search_query = build_search_query(query, history)

        t0 = perf_counter()
        context, sources = retrieve_context(
            search_query, document=request.document
        )
        print(f"retrieval: {perf_counter() - t0:.1f}s")

        if not context:
            return {
                "question": query,
                "answer": NOT_FOUND_MESSAGE,
                "sources": []
            }

        t1 = perf_counter()
        answer = generate_answer(query, context, history)
        print(f"generation: {perf_counter() - t1:.1f}s")

        if answer == NOT_FOUND_MESSAGE:
            return {
                "question": query,
                "answer": NOT_FOUND_MESSAGE,
                "sources": []
            }

        return {
            "question": query,
            "answer": answer,
            "sources": unique_sources(sources)
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Answer generation failed: {str(e)}"
        )


@app.post("/ask_stream")
def ask_stream(request: QuestionRequest):
    """Streams the answer word by word as newline-delimited JSON."""

    query = request.question.strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    history = [turn.model_dump() for turn in request.history]

    def event(data):
        return json.dumps(data, ensure_ascii=False) + "\n"

    def generate():
        try:
            reply = small_talk_reply(query)

            if reply:
                yield event({"type": "token", "text": reply})
                yield event({"type": "sources", "sources": []})
                return

            # Follow-ups like "give formula for this rate" also search
            # with the previous question so "this" has a meaning
            search_query = build_search_query(query, history)

            t0 = perf_counter()
            context, sources = retrieve_context(
                search_query, document=request.document
            )
            print(f"retrieval: {perf_counter() - t0:.1f}s")

            if not context:
                yield event({"type": "not_found", "text": NOT_FOUND_MESSAGE})
                return

            t1 = perf_counter()
            first_token = True

            for kind, text in stream_answer(query, context, history):

                if kind == "not_found":
                    yield event(
                        {"type": "not_found", "text": NOT_FOUND_MESSAGE}
                    )
                    return

                if first_token:
                    print(f"first token after: {perf_counter() - t1:.1f}s")
                    first_token = False

                yield event({"type": "token", "text": text})

            print(f"generation: {perf_counter() - t1:.1f}s")

            yield event({
                "type": "sources",
                "sources": unique_sources(sources)
            })

        except Exception as e:
            yield event({
                "type": "error",
                "text": f"Answer generation failed: {str(e)}"
            })

    return StreamingResponse(generate(), media_type="application/x-ndjson")


# Serve the uploaded PDFs so references can open them: /pdfs/<file>.pdf#page=5
app.mount("/pdfs", StaticFiles(directory=str(UPLOAD_DIR)), name="pdfs")

# Serve the frontend from the backend: open http://127.0.0.1:8001/app/
FRONTEND_DIR = Path("frontend")

if FRONTEND_DIR.exists():
    app.mount(
        "/app",
        StaticFiles(directory=str(FRONTEND_DIR), html=True),
        name="frontend"
    )