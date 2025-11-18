# OIRA Chatbot Backend

FastAPI backend for the Bucknell University course catalog chatbot.

## Features

- **RAG (Retrieval-Augmented Generation)**: Uses ChromaDB to retrieve relevant course information and OpenAI to generate answers
- **Session Management**: Tracks conversation history using SQLite
- **Feedback System**: Allows users to rate assistant responses with thumbs up/down
- **Message History**: Retrieves full conversation history for session restoration

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

#### Schedule OCR requirement

Screenshot uploads for the schedule assistant depend on the Tesseract OCR binary. Install it on your system before uploading PNG/JPG files:

- **macOS:** `brew install tesseract`
- **Ubuntu/Debian:** `sudo apt-get update && sudo apt-get install -y tesseract-ocr`
- **Windows:** Use the [UB Mannheim installer](https://github.com/UB-Mannheim/tesseract/wiki) and add the install directory to your `PATH`.

If Tesseract is missing you will only be able to ingest plain text/CSV schedules.

### 2. Configure Environment Variables

Create or update `.env` file with your OpenAI API key:

```
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-large
DATABASE_URL=sqlite:///./chatbot.db
CHROMA_PATH=chroma_db
DATA_PATH=data
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
```

### 3. Ingest Course Catalog Data

Place your course catalog PDFs in the `data/` folder, then run:

```bash
python ingest_database.py
```

This will:
- Load PDFs from the data directory
- Split documents into chunks
- Generate embeddings using OpenAI
- Store embeddings in ChromaDB

### 4. Run the API Server

```bash
python main.py
```

Or with uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Public Endpoints

#### `POST /chat`
Ask a question and get an answer with citations.

**Request:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "What courses are available for Computer Science majors?"
}
```

**Response:**
```json
{
  "message_id": 123,
  "answer": "Based on the course catalog...",
  "citations": [
    {
      "content": "CSCI 101: Introduction to Computer Science...",
      "source": "2025-2026 course catalog.pdf",
      "page": 45
    }
  ],
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### `POST /feedback`
Submit thumbs up/down feedback for an assistant message.

**Request:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message_id": 123,
  "rating": 1,
  "note": "Very helpful!"
}
```

**Response:**
```json
{
  "success": true,
  "feedback_id": 456
}
```

#### `GET /messages?session_id={session_id}`
Retrieve conversation history for a session.

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "messages": [
    {
      "id": 122,
      "role": "user",
      "content": "What courses are available?",
      "citations": null,
      "created_at": "2025-11-12T10:30:00"
    },
    {
      "id": 123,
      "role": "assistant",
      "content": "Based on the catalog...",
      "citations": [...],
      "created_at": "2025-11-12T10:30:05"
    }
  ]
}
```

### Admin Endpoints

#### `POST /admin/ingest`
Trigger re-ingestion of PDFs from the data folder. (Note: Add authentication in production)

## Architecture

### Data Flow

**Chat Flow:**
1. User sends message to `/chat` with session_id
2. Backend creates session if needed
3. Logs user message to SQLite
4. Retrieves top-K relevant chunks from ChromaDB
5. Calls OpenAI to generate answer with context
6. Logs assistant response with citations
7. Returns answer and message_id

**Feedback Flow:**
1. User clicks thumbs up/down on message
2. Frontend calls `/feedback` with message_id and rating
3. Backend stores feedback in SQLite
4. Used for analytics (doesn't modify knowledge base)

**Session Restoration:**
1. User returns to app
2. Frontend retrieves session_id from localStorage
3. Calls `/messages?session_id=...`
4. Displays full conversation history

### Database Schema

**sessions table:**
- session_id (PK)
- created_at
- updated_at

**messages table:**
- id (PK, auto-increment)
- session_id
- role (user/assistant)
- content
- citations (JSON)
- created_at

**feedback table:**
- id (PK, auto-increment)
- session_id
- message_id
- rating (1 or -1)
- note (optional)
- created_at

## Files

- `main.py`: FastAPI application with API endpoints
- `chatbot_service.py`: RAG logic (ChromaDB + OpenAI)
- `database.py`: SQLAlchemy models and session management
- `models.py`: Pydantic request/response models
- `config.py`: Configuration and environment variables
- `ingest_database.py`: Script to ingest PDFs into ChromaDB
- `chatbot.py`: Original Gradio demo (kept for reference)

## Testing the API

You can test the API using the interactive docs at `http://localhost:8000/docs` (Swagger UI) or `http://localhost:8000/redoc` (ReDoc).

Example using curl:

```bash
# Chat
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-123", "message": "What is CSCI 101?"}'

# Get messages
curl "http://localhost:8000/messages?session_id=test-123"

# Submit feedback
curl -X POST "http://localhost:8000/feedback" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-123", "message_id": 1, "rating": 1}'
```

## Notes

- Session IDs should be UUIDs generated by the frontend
- Citations are stored as JSON strings in SQLite
- The chatbot uses conversation history (last 6 messages) for context
- ChromaDB updates don't require server restart
- CORS is configured for localhost:3000 and localhost:3001 by default
