import glob
import json
import threading
import uuid
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
    build_chat_messages,
    CHAT_OPTIONS,
    stream_messages,
    chat_messages,
    small_talk_reply,
    build_search_query,
    sample_pdf_text,
    generate_summary,
    warm_up as warm_up_llm,
    NOT_FOUND_MESSAGE
)
from backend.broad_queries import plan_special_query
from backend.quiz import quiz_events
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

# A PDF in one of these stages cannot be re-uploaded yet.
# Deleting is always allowed: it stops the indexing job.
ACTIVE_STAGES = {"queued", "text", "tables", "summary", "images"}

# Every upload gets a job id. Deleting a PDF removes its id, which tells a
# running (or waiting) background job to stop and clean up after itself.
jobs = {}

# PDFs Windows would not let us delete yet because indexing still had them open
deferred_deletes = set()


class JobCancelled(Exception):
    pass


def is_being_processed(filename):
    return processing_status.get(filename, {}).get("stage") in ACTIVE_STAGES


def job_is_current(name, job):
    return jobs.get(name) == job


def begin_stage(name, job, stage):
    """Stops the job if the PDF was deleted, otherwise records the new stage."""
    if not job_is_current(name, job):
        raise JobCancelled()

    set_status(name, stage)


def set_status(filename, stage, error=None, detail=None):
    warnings = (
        []
        if stage == "queued"
        else processing_status.get(filename, {}).get("warnings", [])
    )
    processing_status[filename] = {
        "stage": stage,
        "error": error,
        "detail": detail,
        "warnings": warnings
    }


def add_warning(filename, text):
    entry = processing_status.setdefault(
        filename, {"stage": "queued", "error": None, "warnings": []}
    )
    entry["warnings"].append(text)


def purge_index(name):
    """Removes every stored trace of a PDF: vector records and extracted images."""
    for collection in (text_collection, table_collection, image_collection):
        try:
            collection.delete(where={"source": name})
        except Exception as e:
            print(f"Could not clear {name} from a collection: {e}")

    stem = glob.escape(Path(name).stem)

    for image_file in Path("data/extracted_images").glob(f"{stem}_page*"):
        try:
            image_file.unlink()
        except OSError:
            pass


def finish_deferred_delete(file_path):
    if file_path.name not in deferred_deletes:
        return

    try:
        file_path.unlink(missing_ok=True)
        deferred_deletes.discard(file_path.name)
    except OSError as e:
        print(f"Still cannot delete {file_path.name}: {e}")


def run_pipeline(file_path, name, job):
    total = perf_counter()

    # 1. Text first: it answers most questions
    begin_stage(name, job, "text")
    t = perf_counter()
    try:
        ingest_pdf_text(file_path)
        print(f"text ingestion: {perf_counter() - t:.1f}s")
    except Exception as e:
        print(f"Text ingestion failed for {name}: {e}")
        if job_is_current(name, job):
            set_status(name, "error", error=f"Reading the text failed: {e}")
        return

    # 2. Tables
    begin_stage(name, job, "tables")
    t = perf_counter()
    try:
        ingest_pdf_tables(file_path)
        print(f"table ingestion: {perf_counter() - t:.1f}s")
    except Exception as e:
        print(f"Table ingestion failed for {name}: {e}")
        add_warning(name, "tables skipped")

    # 3. Summary + suggested questions (uses the already-loaded answer model)
    begin_stage(name, job, "summary")
    t = perf_counter()
    try:
        sample = sample_pdf_text(file_path)
        result = generate_summary(sample) if sample else None

        if result and job_is_current(name, job):
            summaries[name] = result
            save_summaries()

        print(f"summary: {perf_counter() - t:.1f}s")
    except Exception as e:
        print(f"Summary skipped for {name}: {e}")

    # 4. Images (slowest). Stops between images if the PDF is deleted.
    begin_stage(name, job, "images")
    t = perf_counter()

    def report_progress(done, count):
        if job_is_current(name, job):
            set_status(name, "images", detail=f"{done}/{count}")

    try:
        result = ingest_pdf_images(
            file_path,
            should_cancel=lambda: not job_is_current(name, job),
            on_progress=report_progress,
        )
        print(f"image ingestion: {perf_counter() - t:.1f}s {result}")
    except Exception as e:
        print(f"Image ingestion failed for {name}: {e}")
        add_warning(name, "images skipped (is Ollama running?)")

    if not job_is_current(name, job):
        raise JobCancelled()

    set_status(name, "done")
    print(f"All done for {name} in {perf_counter() - total:.0f}s")


def process_pdf(file_path: Path, job: str):
    """Runs in the background: text, tables, summary, then images."""

    name = file_path.name

    with processing_lock:
        try:
            run_pipeline(file_path, name, job)

        except JobCancelled:
            print(f"Indexing of {name} was cancelled, cleaning up")

            purge_index(name)

            if name not in jobs:
                processing_status.pop(name, None)

            finish_deferred_delete(file_path)


NO_PDF_MESSAGE = (
    "📂 PDF Analyzer needs a PDF to read. Upload one on the Documents page, "
    "or switch to Chatbot mode to ask general questions."
)


def has_any_documents():
    return any(
        file.is_file()
        and file.suffix.lower() == ".pdf"
        and file.name not in deferred_deletes
        for file in UPLOAD_DIR.iterdir()
    )


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


class QuizRequest(BaseModel):
    document: str
    count: int = 5                   # 3 to 10
    difficulty: str = "medium"       # easy | medium | hard


class QuestionRequest(BaseModel):
    question: str
    mode: str = "pdf"            # "pdf" = PDF Analyzer, "chat" = Chatbot
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
            if file.is_file()
            and file.suffix.lower() == ".pdf"
            and file.name not in deferred_deletes
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

    label = STAGE_LABELS.get(info["stage"], "")

    if info.get("detail"):
        label = f"{label} ({info['detail']})"

    return {**info, "label": label}


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
    """Deletes a PDF and everything indexed from it. If it is still being
    indexed, the background job is stopped first."""

    # Prevent directory traversal
    if Path(filename).name != filename or not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Invalid PDF filename."
        )

    file_path = UPLOAD_DIR / filename

    if not file_path.exists() or filename in deferred_deletes:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    was_indexing = is_being_processed(filename)

    try:
        # Tell any running or waiting indexing job to stop
        jobs.pop(filename, None)
        processing_status.pop(filename, None)

        # Delete what has been indexed so far (the job clears the rest when it stops)
        purge_index(filename)

        if summaries.pop(filename, None) is not None:
            save_summaries()

        # Delete the PDF itself. Windows refuses while a job still has it open;
        # in that case the job deletes it as soon as it stops.
        try:
            file_path.unlink()
        except PermissionError:
            deferred_deletes.add(filename)

        return {
            "message": (
                "Indexing was stopped and the document was deleted."
                if was_indexing
                else "Document and indexed data deleted successfully."
            ),
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

    if is_being_processed(filename) or filename in deferred_deletes:
        raise HTTPException(
            status_code=409,
            detail=(
                "This PDF is still being processed. Wait for it to finish, "
                "or delete it to stop indexing, then upload again."
            )
        )

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

        job = uuid.uuid4().hex
        jobs[filename] = job

        set_status(filename, "queued")
        background_tasks.add_task(process_pdf, file_path, job)

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
        if request.mode == "chat":
            history = [turn.model_dump() for turn in request.history]
            answer = chat_messages(build_chat_messages(query, history), CHAT_OPTIONS)
            return {"question": query, "answer": answer, "sources": []}

        reply = small_talk_reply(query)

        if reply:
            return {"question": query, "answer": reply, "sources": []}

        if not has_any_documents():
            return {"question": query, "answer": NO_PDF_MESSAGE, "sources": []}

        plan = plan_special_query(query, request.document)

        if plan:
            if plan.get("reply"):
                return {"question": query, "answer": plan["reply"], "sources": []}

            return {
                "question": query,
                "answer": chat_messages(plan["messages"], plan["options"]),
                "sources": unique_sources(plan["sources"])
            }

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
            # Chatbot mode: plain conversation, no documents involved
            if request.mode == "chat":
                for token in stream_messages(
                    build_chat_messages(query, history), CHAT_OPTIONS
                ):
                    yield event({"type": "token", "text": token})

                yield event({"type": "sources", "sources": []})
                return

            reply = small_talk_reply(query)

            if reply:
                yield event({"type": "token", "text": reply})
                yield event({"type": "sources", "sources": []})
                return

            if not has_any_documents():
                yield event({"type": "token", "text": NO_PDF_MESSAGE})
                yield event({"type": "sources", "sources": []})
                return

            # Summaries, key concepts, figures and page questions are built
            # directly from the stored data instead of searching
            plan = plan_special_query(query, request.document)

            if plan:
                if plan.get("reply"):
                    yield event({"type": "token", "text": plan["reply"]})
                    yield event({"type": "sources", "sources": []})
                    return

                for token in stream_messages(plan["messages"], plan["options"]):
                    yield event({"type": "token", "text": token})

                yield event({
                    "type": "sources",
                    "sources": unique_sources(plan["sources"])
                })
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


@app.post("/quiz_stream")
def quiz_stream(request: QuizRequest):
    """Streams quiz questions (one JSON object per line) as they are written."""

    document = Path(request.document).name

    if not (UPLOAD_DIR / document).exists() or document in deferred_deletes:
        raise HTTPException(status_code=404, detail="Document not found.")

    count = max(3, min(request.count, 10))
    difficulty = (
        request.difficulty
        if request.difficulty in ("easy", "medium", "hard")
        else "medium"
    )

    def generate():
        try:
            for item in quiz_events(document, count, difficulty):
                yield json.dumps(item, ensure_ascii=False) + "\n"
        except Exception as e:
            print(f"Quiz generation failed: {e}")
            yield json.dumps(
                {"type": "error", "text": "The quiz could not be generated. Is Ollama running?"}
            ) + "\n"

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