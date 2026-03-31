# OIRA Chatbot

AI-powered Bucknell University course catalog assistant.

This repository contains:

- `backend/`: FastAPI API, RAG ingestion, SQLite persistence, ChromaDB vector store
- `frontend/`: Next.js chat UI with Clerk-based authentication

## Quick start

### 1) Configure environment variables

Backend:

- Copy `backend/.env.example` to `backend/.env`
- Set at least `OPENAI_API_KEY`

Frontend:

- Copy `frontend/.env.example` to `frontend/.env.local`
- Set `NEXT_PUBLIC_API_URL` to `http://localhost:8000` for local development
- Add Clerk keys if auth is enabled

### 2) Start both services

macOS/Linux or Git Bash:

```bash
bash start.sh
```

Windows:

```powershell
./start.ps1
```

Local URLs:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

## Run services separately

### Backend

See [`backend/README.md`](./backend/README.md).

Typical flow:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/ingest_database.py
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

## Repo layout

```text
OIRA-Chatbot/
  backend/    # API, RAG logic, prompts, scripts, tests
  frontend/   # Next.js app
  start.sh    # launches backend and frontend together
  start.ps1   # Windows startup script
```

## How it works

### RAG ingestion lifecycle

1. Put source documents in `backend/data/` and optionally configure `backend/data/google_docs.csv`
2. Run `python backend/scripts/ingest_database.py`
3. The backend stores embeddings in ChromaDB and metadata in SQLite
4. Chat requests retrieve relevant chunks and generate cited answers with OpenAI

### Sessions and feedback

- Sessions and messages are stored in SQLite
- The frontend keeps track of session IDs and can restore previous chats
- Users can submit thumbs up/down feedback on assistant responses

## Testing and utilities

Backend setup check:

```bash
cd backend
python scripts/test_setup.py
```

Backend tests:

```bash
cd backend
pytest tests
```

## Troubleshooting

- Frontend cannot reach backend:
  Confirm the backend is running and `NEXT_PUBLIC_API_URL` is correct.
- CORS errors:
  Check backend `ALLOWED_ORIGINS` in `backend/.env`.
- Ingestion fails:
  Verify `OPENAI_API_KEY`, document paths, and any Google Docs configuration.

## License

Bucknell University - OIRA Chatbot Project
