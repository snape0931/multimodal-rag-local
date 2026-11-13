# 🚀 OmniDoc AI — Local Multimodal RAG System

<p align="center">
  <strong>📄 Chat with your PDFs using Local AI</strong>
  <br/>
  A multimodal document intelligence system that understands and retrieves information from text, tables, and images using Retrieval-Augmented Generation (RAG).
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" />
  <img src="https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi" />
  <img src="https://img.shields.io/badge/Ollama-Local%20LLM-black?logo=ollama" />
  <img src="https://img.shields.io/badge/ChromaDB-Vector%20Database-purple" />
  <img src="https://img.shields.io/badge/JavaScript-Frontend-yellow?logo=javascript" />
</p>

---

## 🌟 Overview

**OmniDoc AI** is a locally running Multimodal Retrieval-Augmented Generation (RAG) application that enables users to interact with PDF documents through natural language queries.

Unlike traditional PDF chatbots that primarily rely on extracted text, OmniDoc AI incorporates three independent retrieval pipelines:

- 📝 **Text Retrieval** — Extracts, chunks, and indexes textual content.
- 📊 **Table Retrieval** — Extracts and processes tabular information.
- 🖼️ **Image Retrieval** — Extracts images and indexes their searchable descriptions.

The retrieved information is combined into a unified context and passed to a locally running Large Language Model (LLM) through Ollama to generate context-aware responses.

**The goal is simple: Make complex PDF documents searchable, understandable, and interactive.**

## ✨ Key Features

- 📄 **Multimodal PDF Processing** — Processes text, tables, and images from PDF documents.
- 🔍 **Semantic Search** — Retrieves relevant information using vector embeddings rather than simple keyword matching.
- 🧠 **Context-Aware Responses** — Generates answers grounded in retrieved document content.
- 🗂️ **Multi-Collection Retrieval** — Maintains separate ChromaDB collections for text, tables, and images.
- 🦙 **Local LLM Integration** — Runs Llama 3.2 locally using Ollama.
- 🔒 **Local Processing** — Keeps LLM inference on the local machine without requiring cloud-based LLM APIs.
- 📌 **Source Attribution** — Uses document metadata, including filenames and page numbers, to trace retrieved information.
- ⚡ **FastAPI Backend** — Provides REST APIs for document ingestion and question answering.
- 💻 **Interactive Web Interface** — Upload PDFs and ask questions through a simple frontend.

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| 🐍 Language | Python |
| ⚙️ Backend | FastAPI, Uvicorn |
| 🎨 Frontend | HTML, CSS, JavaScript |
| 🧠 LLM | Llama 3.2 (3B) |
| 🦙 LLM Runtime | Ollama |
| 🔢 Embeddings | Sentence Transformers (`all-MiniLM-L6-v2`) |
| 🗄️ Vector Database | ChromaDB |
| 📄 PDF Processing | PyMuPDF, pdfplumber, PyPDF |
| 🖼️ Image Processing | Pillow |
| 🔗 API | REST API |

## 🏗️ System Architecture

OmniDoc AI follows a multimodal RAG architecture consisting of two major stages.

### 1️⃣ Document Ingestion Pipeline

When a user uploads a PDF, the system processes its contents through three independent pipelines.

**📝 Text Processing**
- Extracts textual content from PDF pages.
- Splits content into manageable chunks.
- Generates vector embeddings.
- Stores embeddings and metadata in the text collection.

**📊 Table Processing**
- Identifies and extracts tabular information.
- Preserves table structure and associated metadata.
- Converts tables into searchable representations.
- Stores embeddings in a dedicated table collection.

**🖼️ Image Processing**
- Extracts images from PDF pages.
- Generates searchable descriptions of image content.
- Creates embeddings for semantic retrieval.
- Stores image descriptions and metadata in a dedicated image collection.

### 2️⃣ Query Processing Pipeline

When a user submits a question:

1. 💬 The question is converted into a vector embedding.
2. 🔍 Semantic similarity search is performed across all three collections.
3. 📚 Relevant text, table, and image results are retrieved.
4. 🔗 Retrieved information is combined into a unified context.
5. 🧠 The context and user query are passed to Llama 3.2 through Ollama.
6. ✨ The LLM generates a context-aware response.
7. 📌 Source metadata helps identify the relevant documents and pages.

### 🔄 Architecture Flow

```text
                  👤 USER
                     |
                     v
              💻 Web Interface
                     |
                     v
              ⚙️ FastAPI Backend
                     |
                     v
              📄 PDF Upload
                     |
                     v
            🔄 Document Processing
                     |
          +----------+----------+
          |          |          |
          v          v          v
       📝 Text     📊 Tables   🖼️ Images
      Extraction  Extraction  Extraction
          |          |          |
          v          v          v
       Chunking   Processing  Description
          |          |          |
          v          v          v
      Embeddings Embeddings Embeddings
          |          |          |
          +----------+----------+
                     |
                     v
              🗄️ ChromaDB
                     |
                     v
               💬 User Query
                     |
                     v
              🔍 Semantic Search
                     |
                     v
              📚 Context Retrieval
                     |
                     v
              🦙 Ollama LLM
                (Llama 3.2)
                     |
                     v
              ✨ Generated Answer
                     |
                     v
                💻 Web Interface
```

## 📁 Project Structure

```text
multimodal-rag-local/
│
├── backend/
│   ├── __init__.py
│   ├── ingestion.py
│   ├── table_ingestion.py
│   ├── image_ingestion.py
│   ├── retrieval.py
│   └── generation.py
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
│
├── data/
│   ├── documents/
│   └── extracted_images/
│
├── app.py
├── image_extractor.py
├── image_ingest.py
├── ingest.py
├── rag_pipeline.py
├── table_extractor.py
├── table_ingest.py
├── check_database.py
├── requirements.txt
└── README.md
```

## ⚙️ Installation & Setup

### 📌 Prerequisites

- Python 3.10+
- Ollama
- Git

### 1. 📥 Clone the Repository

```bash
git clone https://github.com/snape0931/multimodal-rag-local.git

cd multimodal-rag-local
```

### 2. 🐍 Create a Virtual Environment

```bash
python -m venv venv
```

Activate it:

**Windows:**
```bash
venv\Scripts\activate
```

**Linux / macOS:**
```bash
source venv/bin/activate
```

### 3. 📦 Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. 🦙 Configure Ollama

Download Ollama:

👉 https://ollama.com/download

Pull the model:

```bash
ollama pull llama3.2:3b
```

Start the Ollama server:

```bash
ollama serve
```

Keep the server running while using the application.

### 5. ⚡ Start the Backend

```bash
uvicorn backend.main:app --reload
```

### 6. 🌐 Launch the Frontend

Open `frontend/index.html` using VS Code Live Server or another local development server.

🎉 You're ready to upload PDFs and start asking questions!

## 💡 Example Use Cases

- 📚 Understanding lengthy academic research papers.
- 📊 Retrieving numerical information from PDF tables.
- 🖼️ Finding information associated with figures and diagrams.
- 📖 Summarizing technical documentation.
- 🔗 Answering questions requiring information from multiple sections.
- 🎓 Interacting with lecture notes and educational material.

## 🧩 Engineering Highlights

| Feature | Implementation |
|---|---|
| Multimodal ingestion | Independent text, table, and image pipelines |
| Semantic retrieval | Sentence Transformer embeddings |
| Vector storage | Separate ChromaDB collections |
| Context construction | Aggregation of retrieved multimodal evidence |
| Local inference | Ollama with Llama 3.2 |
| API architecture | FastAPI-based modular backend |

## 🔮 Future Improvements

- ⚡ Streaming responses for lower perceived latency.
- 🎯 Advanced reranking for improved retrieval accuracy.
- 💬 Conversation history and contextual follow-up questions.
- 📂 Multiple document uploads and cross-document querying.
- 👁️ Vision-language model integration for deeper image understanding.
- 🗑️ Document management with deletion and re-indexing.
- 🐳 Docker-based deployment and containerization.

## 👨‍💻 Author

**Saumya Srivastava**

🎓 BITS Pilani, K. K. Birla Goa Campus

🔗 GitHub: [@snape0931](https://github.com/snape0931)

---

<p align="center">
  ⭐ If you find this project interesting, consider giving the repository a star!
  <br/><br/>
  <strong>🚀 OmniDoc AI — Turning Documents into Conversations.</strong>
</p>
