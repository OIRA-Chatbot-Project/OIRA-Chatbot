# OIRA Chatbot Backend

FastAPI backend for the Bucknell University course catalog chatbot.

## What this service does

- Exposes the HTTP API used by the frontend chat UI
- Implements RAG (Retrieval-Augmented Generation)
- Ingests PDFs and optional Google Docs content
- Stores embeddings in ChromaDB and app data in SQLite
- Supports session history, feedback, and schedule parsing

## Current structure

```text
backend/
  core/       # config, database setup, models, auth helpers
  routes/     # FastAPI route modules
  services/   # chat, schedule, and Google Docs logic
  scripts/    # ingestion, migrations, setup checks
  prompts/    # prompt templates used by the backend
  tests/      # backend tests
  data/       # source documents and Google Docs CSV/cache
  main.py     # FastAPI app entry point
```

## Tech stack

- FastAPI + Uvicorn
- SQLAlchemy + SQLite
- LangChain + ChromaDB
- OpenAI chat + embeddings
- Optional OCR support (Tesseract via `pytesseract`) for schedule image uploads

## Prerequisites

- Python 3.8+
- OpenAI API key
- Optional: Tesseract OCR if using schedule image uploads

### Install Tesseract (optional)

- macOS: `brew install tesseract`
- Ubuntu/Debian: `sudo apt-get update && sudo apt-get install -y tesseract-ocr`
- Windows: install the UB Mannheim build and add it to `PATH`

## Setup

### 1) Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

- macOS/Linux: `source .venv/bin/activate`
- Windows: `.venv\Scripts\activate`

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Configure environment variables

Copy the example file:

```bash
cp .env.example .env
```

Minimum required:

- `OPENAI_API_KEY=...`

Common settings:

- `OPENAI_MODEL` default: `gpt-4.1-mini`
- `OPENAI_LIGHT_MODEL` default: `gpt-4.1-nano`
- `EMBEDDING_MODEL` default: `text-embedding-3-large`
- `DATABASE_URL` default: `sqlite:///./chatbot.db`
- `CHROMA_PATH` and `CHROMA_COLLECTION_NAME`
- `ALLOWED_ORIGINS` for frontend CORS
- `GOOGLE_DOCS_CSV`, `GOOGLE_DOCS_CACHE_DIR`, `GOOGLE_DOCS_ONLY`

## Ingest data

### PDFs

1. Put source PDFs in `data/`
2. Run:

```bash
python scripts/ingest_database.py
```

### Google Docs

1. Populate `data/google_docs.csv` with rows like:

```csv
filename,doc_type,url
2025-2026 course catalog,catalog,https://docs.google.com/document/d/<id>/edit?usp=sharing
```

2. Ensure the docs are shared with at least Viewer access
3. Run:

```bash
python scripts/ingest_database.py
```

Notes:

- Converted Google Docs are cached under `data/google_docs_cache/`
- `GOOGLE_DOCS_ONLY=true` ingests only Google Docs sources
- The ingester can prefer markdown catalog exports in `data/` when present

## Run the server

### Option A: Python

```bash
python main.py
```

### Option B: Uvicorn

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Available endpoints:

- API root: `http://localhost:8000/`
- Swagger UI: `http://localhost:8000/docs`

## Testing and diagnostics

Quick environment check:

```bash
python scripts/test_setup.py
```

Run tests:

```bash
pytest tests
```

Other useful scripts:

- `python scripts/migrate_db.py`
- `python scripts/add_session_title_column.py`
- `python scripts/recreate_db.py`

## Troubleshooting

- Frontend cannot reach backend:
  Confirm `ALLOWED_ORIGINS` includes `http://localhost:3000` and the backend is running.
- Retrieval results look wrong:
  Re-run `python scripts/ingest_database.py` and confirm `CHROMA_PATH` and `CHROMA_COLLECTION_NAME` are consistent.
- ChromaDB directory is missing:
  Run ingestion first to create the vector store.
- OCR is not working:
  Confirm the system `tesseract` binary is installed and available in `PATH`.
