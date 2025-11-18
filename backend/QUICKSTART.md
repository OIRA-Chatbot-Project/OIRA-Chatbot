# OIRA Chatbot - Quick Start Guide

## 📋 What You Have

Your FastAPI backend is now fully implemented with the following components:

### Core Files
- **`main.py`** - FastAPI application with all endpoints (/chat, /feedback, /messages, /admin/ingest)
- **`chatbot_service.py`** - RAG service integrating ChromaDB and OpenAI
- **`database.py`** - SQLAlchemy models for sessions, messages, and feedback
- **`models.py`** - Pydantic schemas for request/response validation
- **`config.py`** - Centralized configuration from environment variables

### Existing Files (Preserved)
- **`ingest_database.py`** - PDF ingestion script (unchanged)
- **`chatbot.py`** - Original Gradio demo (kept for reference)

### New Utility Files
- **`test_setup.py`** - Verify your setup is correct
- **`test_api.py`** - Test the API endpoints interactively
- **`run.sh`** - Helper script for common tasks
- **`README.md`** - Comprehensive documentation

## 🚀 Getting Started

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

#### Schedule OCR requirement

Uploading screenshots of schedules relies on the Tesseract OCR binary in addition to the Python packages above. Install it once on your system:

- **macOS:** `brew install tesseract`
- **Ubuntu/Debian:** `sudo apt-get update && sudo apt-get install -y tesseract-ocr`
- **Windows:** Download the installer from [UB Mannheim builds](https://github.com/UB-Mannheim/tesseract/wiki) and add the installation folder to your `PATH`.

Without Tesseract the backend cannot read PNG/JPG uploads and schedule parsing will fail.

### Step 2: Verify Setup

```bash
python test_setup.py
```

This will check:
- ✓ All required packages are installed
- ✓ Environment variables are set
- ✓ Database can be initialized
- ✓ ChromaDB connection works

### Step 3: Ingest Course Catalog (If Not Done)

Make sure you have PDF files in the `data/` folder, then:

```bash
python ingest_database.py
```

### Step 4: Start the Server

**Development mode (with auto-reload):**
```bash
python main.py
```

Or:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Production mode:**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Step 5: Test the API

**Option 1: Interactive Swagger UI**
- Open browser: http://localhost:8000/docs
- Try out the endpoints directly

**Option 2: Python Test Client**
```bash
python test_api.py
```
Select option 1 for full test suite or option 2 for interactive chat.

**Option 3: Manual cURL**
```bash
# Health check
curl http://localhost:8000/

# Chat
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-123", "message": "What is CSCI 101?"}'

# Get messages
curl "http://localhost:8000/messages?session_id=test-123"
```

## 📡 API Endpoints

### `GET /`
Health check - returns API status and version

### `POST /chat`
**Request:**
```json
{
  "session_id": "uuid-here",
  "message": "Your question"
}
```

**Response:**
```json
{
  "message_id": 123,
  "answer": "The answer...",
  "citations": [...],
  "session_id": "uuid-here"
}
```

### `POST /feedback`
**Request:**
```json
{
  "session_id": "uuid-here",
  "message_id": 123,
  "rating": 1,  // 1 for 👍, -1 for 👎
  "note": "Optional feedback"
}
```

### `GET /messages?session_id=xxx`
Returns full conversation history for a session

### `POST /admin/ingest`
Triggers PDF re-ingestion (admin only)

## 🗄️ Database Schema

### SQLite Tables (auto-created)

**sessions**
- session_id (PK) - UUID from frontend
- created_at - Timestamp
- updated_at - Timestamp

**messages**
- id (PK) - Auto-increment
- session_id - Links to session
- role - "user" or "assistant"
- content - Message text
- citations - JSON array (for assistant messages)
- created_at - Timestamp

**feedback**
- id (PK) - Auto-increment
- session_id - Links to session
- message_id - Links to message
- rating - 1 (👍) or -1 (👎)
- note - Optional text
- created_at - Timestamp

## 🔄 Data Flows

### Chat Flow
1. Frontend sends POST to `/chat` with session_id and message
2. Backend creates/updates session in SQLite
3. Stores user message in database
4. Retrieves top-5 relevant chunks from ChromaDB
5. Sends question + chunks + history to OpenAI
6. Stores assistant response with citations
7. Returns answer and message_id to frontend

### Feedback Flow
1. User clicks 👍 or 👎 on a message
2. Frontend sends POST to `/feedback`
3. Backend validates message exists
4. Stores rating and optional note in database
5. Returns success confirmation

### Session Restoration
1. User returns to app with saved session_id
2. Frontend calls GET `/messages?session_id=xxx`
3. Backend retrieves full conversation history
4. Returns all messages with citations
5. Frontend displays conversation

## 🔧 Configuration

Edit `.env` file:

```env
# Required
OPENAI_API_KEY=sk-...

# Optional (defaults shown)
OPENAI_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-large
DATABASE_URL=sqlite:///./chatbot.db
CHROMA_PATH=chroma_db
DATA_PATH=data
NUM_RETRIEVAL_RESULTS=5
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
```

## 🧪 Testing

1. **Setup Test**: `python test_setup.py`
2. **API Test**: `python test_api.py`
3. **Swagger UI**: http://localhost:8000/docs
4. **ReDoc**: http://localhost:8000/redoc

## 📝 Next Steps for Frontend

Your Next.js frontend should:

1. **Generate session_id** when user clicks "New Chat"
   ```typescript
   const sessionId = crypto.randomUUID()
   localStorage.setItem('sessionId', sessionId)
   ```

2. **Send chat messages**
   ```typescript
   const response = await fetch('http://localhost:8000/chat', {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({ session_id: sessionId, message: userInput })
   })
   const data = await response.json()
   // Use data.answer, data.citations, data.message_id
   ```

3. **Load conversation history**
   ```typescript
   const response = await fetch(
     `http://localhost:8000/messages?session_id=${sessionId}`
   )
   const data = await response.json()
   // data.messages contains full history
   ```

4. **Submit feedback**
   ```typescript
   await fetch('http://localhost:8000/feedback', {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({
       session_id: sessionId,
       message_id: messageId,
       rating: 1, // or -1
       note: optionalNote
     })
   })
   ```

## 🐛 Troubleshooting

**"Module not found" errors**
- Run: `pip install -r requirements.txt`

**"OPENAI_API_KEY not set"**
- Add your API key to `.env` file

**"ChromaDB not found"**
- Run: `python ingest_database.py`

**CORS errors from frontend**
- Add your frontend URL to ALLOWED_ORIGINS in `.env`

**Database errors**
- Delete `chatbot.db` and restart server (tables will be recreated)

## 📚 Additional Resources

- FastAPI docs: https://fastapi.tiangolo.com
- LangChain docs: https://python.langchain.com
- ChromaDB docs: https://docs.trychroma.com
- OpenAI API: https://platform.openai.com/docs

---

**You're all set! 🎉**

Start the server and begin testing with the API!
