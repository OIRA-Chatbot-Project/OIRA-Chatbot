# OIRA Chatbot Backend

FastAPI backend for the Bucknell University course catalog chatbot.

## What this service does

- Provides the HTTP API used by the frontend chat UI
- Implements RAG (Retrieval-Augmented Generation):
  - Ingests PDFs / Google Docs content
  - Creates embeddings using OpenAI
  - Stores embeddings in ChromaDB
  - Retrieves relevant chunks during chat
- Persists sessions, messages, and feedback in SQLite (via SQLAlchemy)

## Tech stack

- FastAPI + Uvicorn
- SQLAlchemy + SQLite
- LangChain + ChromaDB
- OpenAI (chat + embeddings)
- Optional OCR support (Tesseract via `pytesseract`) for schedule image uploads

## Prerequisites

- Python 3.8+
- OpenAI API key
- (Optional) Tesseract OCR binary if using schedule image uploads

### Install Tesseract (optional)

- macOS: `brew install tesseract`
- Ubuntu/Debian: `sudo apt-get update && sudo apt-get install -y tesseract-ocr`
- Windows: UB Mannheim installer + add to PATH

## Setup

### 1) Create virtual environment

```bash
python -m venv .venv
```

Activate:

- macOS/Linux: `source .venv/bin/activate`
- Windows: `.venv\\Scripts\\activate`

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Configure environment variables

Copy:

```bash
cp .env.example .env
```

Minimum required:

- `OPENAI_API_KEY=...`

Common settings (see `.env.example` for full list):

- `OPENAI_MODEL` (default: `gpt-4o-mini`)
- `EMBEDDING_MODEL` (default: `text-embedding-3-large`)
- `DATABASE_URL` (default: sqlite)
- `CHROMA_PATH` / `CHROMA_COLLECTION_NAME`
- `ALLOWED_ORIGINS` (CORS; include `http://localhost:3000` for local frontend)

## Ingest data (build the knowledge base)

### PDFs

1. Put PDFs in `backend/data/`
2. Run:

```bash
python ingest_database.py
```

### Google Docs (optional / supported)

1. Populate `backend/data/google_docs.csv` with:

```csv
filename,doc_type,url
2025-2026 course catalog,catalog,https://docs.google.com/document/d/<id>/edit?usp=sharing
```

2. Ensure docs are shared with at least Viewer access
3. Run:

```bash
python ingest_database.py
```

Notes:

- The ingester will cache converted docs into a local cache directory (see env vars)
- `GOOGLE_DOCS_ONLY=true` ingests only Google Docs

## Run the server

### Option A: run via Python

```bash
python main.py
```

### Option B: run via uvicorn

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API docs:

- Swagger UI: http://localhost:8000/docs

## Testing / diagnostics

```bash
python test_setup.py
```

## Troubleshooting

- **CORS errors**
  - Ensure `ALLOWED_ORIGINS` includes `http://localhost:3000`
- **Chroma / retrieval issues**
  - Re-run ingestion
  - Confirm `CHROMA_PATH` and `CHROMA_COLLECTION_NAME` match what ingestion used
- **OCR not working**
  - Confirm system `tesseract` is installed and in PATH
