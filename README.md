# OmniDoc AI: local multimodal document assistant

Ask questions about your PDFs, quiz yourself on them, or just chat. Everything runs **on your own computer**: no cloud API, no API keys, and your documents never leave your machine.

OmniDoc AI reads the **text**, **tables** and **figures** of a PDF, answers with page citations, and can open the cited page right next to the chat.


<img width="1874" height="887" alt="image" src="https://github.com/user-attachments/assets/8a81d4ef-1cd1-4c57-9a8c-ef4a7a109144" />


---

## Features

**Three modes in one app**

| Mode | What it does |
|---|---|
| 📄 **PDF Analyzer** | Answers only from your uploaded PDFs, with page citations. Says so when the answer isn't in them. |
| 💬 **Chatbot** | A general assistant for study doubts, coding, maths and writing. No PDF needed. Code answers render in blocks with a Copy button. |
| 🎯 **Quiz Me** | Writes multiple-choice questions from one of your PDFs (5 or 10 questions, easy / medium / hard), keeps score and remembers your best result. |

**Document understanding**
- Text, **tables** (row by row, with headers) and **figures** (embedded images and vector diagrams, described by a vision model) are indexed separately and searched together.
- Retrieval uses embeddings plus a **cross-encoder reranker**, and a relevance cutoff so the model isn't asked to answer from unrelated text.
- Special questions that normal search can't answer work too: *"Summarize this document"*, *"Find important concepts"*, *"Explain a diagram"*, *"Summarize page 3"*.
- An automatic **summary and suggested questions** appear after each upload. A **✨ Summary** button on every document reopens them.

**Interface**
- **Split-screen reading:** click a citation like `p. 5` and that PDF page opens beside the chat.
- **Command palette** (`Ctrl + K`) for navigation, modes, themes and questions.
- **Accent themes** (purple, teal, sunset) and light / dark mode.
- Drag-and-drop upload, live indexing progress, a celebration when a document is ready, and skeleton loaders.
- Streaming answers, a Stop button, and a copy button on answers.
- Deleting a PDF while it is still indexing **stops the job** and cleans up.

---

## How it works

```
PDF upload
   │
   ├─ text    → 800-character overlapping chunks ─┐
   ├─ summary → sampled pages → summary + questions │
   ├─ tables  → one record per row (with headers) ──┤→ embeddings → ChromaDB
   └─ figures → embedded images + vector diagrams   │     (3 collections)
                → LLaVA description → embedding ───┘

Question
   │
   ├─ summary / concepts / diagram / "page N"  → built directly from stored data
   └─ everything else:
        embed question → top matches per collection → cross-encoder rerank
        → drop low scores → llama3.2 answers using only those excerpts
          (replies NOT_FOUND if the answer isn't there)
```

Quiz Me picks passages spread evenly across the PDF and writes one question per passage, so each question has a reliable page number. The correct answer and wrong answers are generated separately and shuffled in code.

---

## Tech stack

| Part | Technology |
|---|---|
| Backend | FastAPI, Uvicorn |
| Vector store | ChromaDB (persistent, local) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| PDF parsing | PyMuPDF (text, tables, images, vector drawings) |
| Language model | `llama3.2:3b` via Ollama |
| Vision model | `llava:7b` via Ollama |
| Frontend | Plain HTML, CSS and JavaScript (no build step) |

---

## Getting started

### 1. Requirements

- **Python 3.10 or newer**
- **[Ollama](https://ollama.com/download)** installed and running
- About **8 GB of RAM** (more is better) and ~8 GB of free disk space for the models

### 2. Install the models

```bash
ollama pull llama3.2:3b
ollama pull llava:7b
```

### 3. Install the Python packages

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
```

### 4. First run on a new computer: allow the model download

`backend/retrieval.py` sets Hugging Face to **offline mode** so the app starts fast and avoids rate limits. That only works once the embedding models are already on your computer. On the **first run**, allow the download:

```powershell
# Windows PowerShell
$env:HF_HUB_OFFLINE = "0"
python -m uvicorn backend.main:app --port 8001
```

```bash
# macOS / Linux
HF_HUB_OFFLINE=0 python -m uvicorn backend.main:app --port 8001
```

After the models have downloaded once, start the app normally (next step).

### 5. Run

From the project root (the folder that contains `backend/` and `frontend/`):

```bash
python -m uvicorn backend.main:app --port 8001
```

Open **http://127.0.0.1:8001/app/** in your browser. Interactive API docs are at `http://127.0.0.1:8001/docs`.

---

## Using the app

1. **Upload** a PDF on the Documents page (button or drag and drop). A progress line shows the stages: text, summary, tables, images.
2. As soon as the text and summary are done, you'll see the summary card and a celebration, and you can start asking questions. Figures keep being described in the background.
3. Go to **Ask AI** and pick a mode:
   - **PDF Analyzer:** choose a document in the SOURCE box (or ask across all of them).
   - **Chatbot:** just talk.
   - **Quiz Me:** choose a document, length and difficulty, then press Start. Answer with the mouse or the keys `A`–`D` / `1`–`4`.
4. Click a citation chip (`p. 5`) to open that page in the split view.
5. Press **Ctrl + K** any time for the command palette.

---

## Project structure

```
RAG/
├─ backend/
│  ├─ main.py             # FastAPI app: upload, status, summary, ask, quiz, delete
│  ├─ retrieval.py        # models, ChromaDB collections, search + rerank
│  ├─ generation.py       # prompts, streaming answers, chatbot, summary generation
│  ├─ broad_queries.py    # summary / concepts / diagram / "page N" questions
│  ├─ quiz.py             # Quiz Me question writer
│  ├─ ingestion.py        # PDF text → chunks → embeddings
│  ├─ table_ingestion.py  # PDF tables → rows → embeddings
│  ├─ image_extractor.py  # embedded images + vector diagrams → PNG files
│  ├─ image_ingestion.py  # figures → LLaVA descriptions → embeddings
│  └─ __init__.py
├─ frontend/
│  ├─ index.html
│  ├─ script.js
│  └─ style.css
├─ data/                  # created at runtime: uploaded PDFs, extracted images, summaries.json
├─ vectorstore/           # created at runtime: ChromaDB files
├─ requirements.txt
└─ README.md
```

`data/` and `vectorstore/` hold your private documents and index. **Don't commit them** (they're in `.gitignore`).

---

## API overview

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Is the backend running? |
| `POST` | `/upload` | Upload a PDF; indexing continues in the background |
| `GET` | `/documents` | List documents with their indexing status |
| `GET` | `/status/{filename}` | Indexing progress for one document |
| `GET` | `/summary/{filename}` | Summary and suggested questions |
| `POST` | `/summary/{filename}/regenerate` | Write the summary again |
| `DELETE` | `/documents/{filename}` | Delete a document (stops indexing if it is running) |
| `POST` | `/ask` | Answer a question (non-streaming) |
| `POST` | `/ask_stream` | Answer a question as a stream; `mode` is `"pdf"` or `"chat"` |
| `POST` | `/quiz_stream` | Stream quiz questions for a document |

---

## Configuration

Small settings live at the top of each file.

| Setting | File | Default | Notes |
|---|---|---|---|
| `ANSWER_MODEL` | `generation.py` | `llama3.2:3b` | Use `llama3.2:1b` for speed, or a larger model for quality |
| `VISION_MODEL` | `image_ingestion.py` | `llava:7b` | `moondream` is much faster on CPU |
| `MAX_IMAGES` | `image_ingestion.py` | `8` | Figures described per PDF |
| `MAX_DESCRIPTION_TOKENS` | `image_ingestion.py` | `150` | Lower is faster but vaguer |
| `MIN_SCORE` | `retrieval.py` | `-4.0` | Relevance cutoff; raise it for stricter answers |
| `TOP_K_FINAL` | `retrieval.py` | `4` | Excerpts sent to the model |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `ingestion.py` | `800` / `150` | Characters per text chunk |
