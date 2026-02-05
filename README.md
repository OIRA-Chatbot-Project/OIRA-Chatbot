# OIRA Chatbot

AI-powered course catalog assistant for Bucknell University.

## 🚀 Quick Start

### One-Command Startup


**Mac/Linux or Git Bash:**
```bash
bash start.sh
```


This will start both the backend API server and frontend UI automatically!

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

## 📋 Prerequisites

- **Python 3.8+** (for backend)
- **Node.js 18+** (for frontend)
- **OpenAI API Key** (configured in `backend/.env`)

## 📁 Project Structure (general)

```
OIRA-Chatbot/
├── backend/              # FastAPI backend
│   ├── main.py          # API endpoints
│   ├── chatbot_service.py
│   ├── database.py
│   ├── ingest_database.py
│   └── requirements.txt
├── frontend/            # Next.js frontend
│   ├── app/
│   ├── package.json
│   |── README.md
|   |__ middleware.ts
├── start.sh             # Startup script (Unix)
```

## 🛠️ Manual Setup

If you prefer to run backend and frontend separately:

### Backend

1. Navigate to backend folder:
   ```bash
   cd backend
   ```

2. Create `.env` file and follow `.env.example` to fill it out


3. Create virtual environment:
   ```bash
   python -m venv .venv
   ```

4. Activate virtual environment:
   - **Windows:** `.venv\Scripts\activate`
   - **Mac/Linux:** `source .venv/bin/activate`

5. Install dependencies and ingest data:
   ```bash
   pip install -r requirements.txt
   python ingest_database.py
   ```

6. Start backend server:
   ```bash
   python main.py
   ```

### Frontend

1. Navigate to frontend folder:
   ```bash
   cd frontend
   ```
2. Create a `.env` file and follow `.env.example` to fill it out

3. Install dependencies:
   ```bash
   npm install
   ```

4. Start development server:
   ```bash
   npm run dev
   ```


   Move to chunking improvements (to keep list/table blocks intact).



## 🎯 Features

- 💬 RAG-powered chatbot with course catalog knowledge
- 📚 Citation tracking with page references
- 👍👎 Feedback system for response quality
- 💾 Session management and chat history
- 🔍 ChromaDB vector search with MMR retrieval
- 🤖 OpenAI GPT-4o-mini integration


## 🧪 Testing

**Test Backend:**
```bash
cd backend
python test_setup.py
python test_api.py
```

**View Database:**
```bash
cd backend
python view_database.py
```

## 📝 License

Bucknell University - OIRA Chatbot Project

## 🤝 Contributors

OIRA Chatbot Project Team
