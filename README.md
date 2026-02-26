# OIRA Chatbot

AI-powered course catalog assistant for Bucknell University.

This repository contains:
- **Backend**: FastAPI + RAG (ChromaDB + LangChain + OpenAI) in [`backend/`](./backend)
- **Frontend**: Next.js chat UI (with Clerk auth) in [`frontend/`](./frontend)

## Quick start (recommended)

### 1) Configure environment variables

Backend:
- Copy `backend/.env.example` → `backend/.env`
- Fill in at least `OPENAI_API_KEY`
  - Optional: Clerk keys if auth is enabled/required in your deployment

Frontend:
- Copy `frontend/.env.example` → `frontend/.env.local`
- Set `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`)
- Add Clerk publishable/secret keys if using auth

### 2) Run both services

**Mac/Linux or Git Bash:**
```bash
bash start.sh
```

**Windows:**
```bash
./start.ps1
```

Services:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Backend API docs (Swagger): http://localhost:8000/docs

## Manual setup (run services separately)

### Backend
See [`backend/README.md`](./backend/README.md).

Typical flow:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # or .venv\\Scripts\\activate on Windows
pip install -r requirements.txt
python ingest_database.py
python main.py
```

### Frontend
See [`frontend/README.md`](./frontend/README.md).

Typical flow:
```bash
cd frontend
npm install
npm run dev
```

## Key concepts

### RAG ingestion lifecycle
1. Put course catalog PDFs in `backend/data/` and/or configure Google Docs links in `backend/data/google_docs.csv`
2. Run `python backend/ingest_database.py`
3. Backend stores embeddings in ChromaDB and metadata in SQLite
4. Chat endpoint retrieves relevant chunks and calls OpenAI to generate answers + citations

### Sessions and feedback
- Sessions are tracked (backend SQLite)
- UI stores session identifiers locally and can restore previous chats
- Users can submit thumbs up/down feedback for assistant messages

## Testing / utilities

Backend quick checks:
```bash
cd backend
python test_setup.py
python test_api.py
```

Inspect DB:
```bash
cd backend
python view_database.py
```

## Troubleshooting

- **Frontend cannot reach backend**
  - Ensure backend is running and `NEXT_PUBLIC_API_URL` is correct
  - Check backend CORS (`ALLOWED_ORIGINS` in `backend/.env`)
- **Ingestion fails**
  - Verify `OPENAI_API_KEY` and model names
  - Ensure PDFs exist in `backend/data/` or Google Docs CSV is valid

## License
Bucknell University - OIRA Chatbot Project