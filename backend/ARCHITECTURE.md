# OIRA Chatbot - System Architecture

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js)                       │
│  - Generates session_id (UUID)                                  │
│  - Stores session_id in localStorage                            │
│  - Renders chat UI with citations                               │
└───────────────┬─────────────────────────────────────────────────┘
                │
                │ HTTP/REST API
                │
┌───────────────▼─────────────────────────────────────────────────┐
│                    FastAPI Backend (main.py)                     │
│                                                                   │
│  Endpoints:                                                      │
│  • POST /chat         - Process user questions                  │
│  • POST /feedback     - Store user ratings                      │
│  • GET  /messages     - Retrieve chat history                   │
│  • POST /admin/ingest - Trigger PDF re-ingestion               │
└─────┬──────────────────────┬──────────────────────┬─────────────┘
      │                      │                      │
      │                      │                      │
┌─────▼──────────┐  ┌────────▼────────┐  ┌─────────▼──────────┐
│  Chatbot       │  │   Database      │  │   ChromaDB         │
│  Service       │  │   (SQLite)      │  │   Vector Store     │
│                │  │                 │  │                    │
│ • RAG Logic    │  │ • sessions      │  │ • Course catalog   │
│ • OpenAI LLM   │  │ • messages      │  │   embeddings       │
│ • Retrieval    │  │ • feedback      │  │ • Semantic search  │
└────────────────┘  └─────────────────┘  └────────────────────┘
```

## 📊 Data Flow Diagrams

### 1. Chat Flow (User Asks Question)

```
┌─────────┐                                    ┌──────────┐
│ User    │                                    │ Frontend │
└────┬────┘                                    └────┬─────┘
     │                                              │
     │ 1. Asks question                            │
     ├─────────────────────────────────────────────>│
     │                                              │
     │                                              │ 2. POST /chat
     │                                              │ {session_id, message}
     │                                              │
     │                                         ┌────▼─────┐
     │                                         │ FastAPI  │
     │                                         │ Backend  │
     │                                         └────┬─────┘
     │                                              │
     │                                              │ 3. Create/Update Session
     │                                         ┌────▼─────┐
     │                                         │ SQLite   │
     │                                         │ sessions │
     │                                         └────┬─────┘
     │                                              │
     │                                              │ 4. Log User Message
     │                                         ┌────▼─────┐
     │                                         │ SQLite   │
     │                                         │ messages │
     │                                         └──────────┘
     │                                              │
     │                                              │ 5. Get Conversation History
     │                                              ├──────────────────┐
     │                                              │                  │
     │                                              │ 6. Query Vector DB
     │                                         ┌────▼─────┐            │
     │                                         │ ChromaDB │            │
     │                                         │ Retriever│            │
     │                                         └────┬─────┘            │
     │                                              │                  │
     │                                              │ Top-K Chunks     │
     │                                              ├<─────────────────┘
     │                                              │
     │                                              │ 7. Build RAG Prompt
     │                                              │ (Question + History + Chunks)
     │                                              │
     │                                         ┌────▼─────┐
     │                                         │ OpenAI   │
     │                                         │ GPT-4o   │
     │                                         └────┬─────┘
     │                                              │
     │                                              │ 8. Generated Answer
     │                                              ├──────────────────┐
     │                                              │                  │
     │                                              │ 9. Log Assistant Response
     │                                         ┌────▼─────┐            │
     │                                         │ SQLite   │            │
     │                                         │ messages │            │
     │                                         └──────────┘            │
     │                                              │                  │
     │                                              │ 10. Return Response
     │                                         ┌────▼─────┐            │
     │                                         │ FastAPI  │<───────────┘
     │                                         │ Response │
     │                                         └────┬─────┘
     │                                              │
     │                                              │ 11. {answer, citations, message_id}
     │                                         ┌────▼─────┐
     │                                         │ Frontend │
     │                                         └────┬─────┘
     │                                              │
     │ 12. Display answer + citations              │
     │<─────────────────────────────────────────────┤
     │                                              │
```

### 2. Feedback Flow (User Rates Answer)

```
┌─────────┐                           ┌──────────┐
│ User    │                           │ Frontend │
└────┬────┘                           └────┬─────┘
     │                                     │
     │ 1. Clicks 👍 or 👎                  │
     ├─────────────────────────────────────>
     │                                     │
     │                                     │ 2. POST /feedback
     │                                     │ {session_id, message_id, rating}
     │                                     │
     │                                ┌────▼─────┐
     │                                │ FastAPI  │
     │                                │ Backend  │
     │                                └────┬─────┘
     │                                     │
     │                                     │ 3. Validate Message Exists
     │                                ┌────▼─────┐
     │                                │ SQLite   │
     │                                │ messages │
     │                                └────┬─────┘
     │                                     │
     │                                     │ 4. Store Feedback
     │                                ┌────▼─────┐
     │                                │ SQLite   │
     │                                │ feedback │
     │                                └────┬─────┘
     │                                     │
     │                                     │ 5. Return Success
     │                                ┌────▼─────┐
     │                                │ Frontend │
     │                                └────┬─────┘
     │                                     │
     │ 6. Show confirmation               │
     │<────────────────────────────────────┤
```

### 3. Session Restoration (User Returns)

```
┌─────────┐                           ┌──────────┐
│ User    │                           │ Frontend │
└────┬────┘                           └────┬─────┘
     │                                     │
     │ 1. Opens app                       │ 2. Load session_id
     ├─────────────────────────────────────> from localStorage
     │                                     │
     │                                     │ 3. GET /messages?session_id=xxx
     │                                     │
     │                                ┌────▼─────┐
     │                                │ FastAPI  │
     │                                │ Backend  │
     │                                └────┬─────┘
     │                                     │
     │                                     │ 4. Retrieve All Messages
     │                                ┌────▼─────┐
     │                                │ SQLite   │
     │                                │ messages │
     │                                └────┬─────┘
     │                                     │
     │                                     │ 5. Return Message History
     │                                ┌────▼─────┐
     │                                │ Frontend │
     │                                └────┬─────┘
     │                                     │
     │ 6. Display full conversation       │
     │<────────────────────────────────────┤
```

### 4. PDF Ingestion Flow (Admin Task)

```
┌─────────┐
│ Admin   │
└────┬────┘
     │
     │ 1. Place PDFs in data/ folder
     │
     │ 2. Run: python ingest_database.py
     │
┌────▼──────────────┐
│ Ingest Script     │
└────┬──────────────┘
     │
     │ 3. Load PDFs
     ├──────────────┐
     │              │
┌────▼─────┐        │
│ PyPDF    │        │
│ Loader   │        │
└────┬─────┘        │
     │              │
     │ 4. Split     │
     ├<─────────────┘
     │
┌────▼─────────────┐
│ Text Splitter    │
│ (300 char chunks)│
└────┬─────────────┘
     │
     │ 5. Generate Embeddings
     │
┌────▼─────────────┐
│ OpenAI           │
│ Embeddings API   │
└────┬─────────────┘
     │
     │ 6. Store Vectors
     │
┌────▼─────────────┐
│ ChromaDB         │
│ (chroma_db/)     │
└──────────────────┘
```

## 🗂️ File Structure

```
backend/
├── main.py                 # FastAPI app with all endpoints
├── chatbot_service.py      # RAG service (OpenAI + ChromaDB)
├── database.py             # SQLAlchemy models (sessions, messages, feedback)
├── models.py               # Pydantic request/response schemas
├── config.py               # Configuration from environment variables
├── ingest_database.py      # PDF ingestion script
├── chatbot.py              # Original Gradio demo (reference)
│
├── .env                    # Environment variables (API keys, config)
├── .env.example            # Template for .env file
├── requirements.txt        # Python dependencies
│
├── test_setup.py           # Setup verification script
├── test_api.py             # Interactive API testing
├── run.sh                  # Helper script for common tasks
│
├── README.md               # Comprehensive documentation
├── QUICKSTART.md           # Quick start guide
├── ARCHITECTURE.md         # This file
│
├── data/                   # PDF course catalogs (input)
├── chroma_db/              # ChromaDB vector store (generated)
└── chatbot.db              # SQLite database (auto-created)
```

## 🔄 Component Interactions

### chatbot_service.py
**Responsibilities:**
- Initialize OpenAI embeddings and LLM
- Connect to ChromaDB vector store
- Retrieve relevant chunks based on query
- Build RAG prompt with context
- Generate answer from LLM
- Extract and format citations

**Used by:** `main.py` (chat endpoint)

### database.py
**Responsibilities:**
- Define SQLAlchemy models
- Manage database connections
- Provide session factory
- Auto-create tables on startup

**Used by:** `main.py` (all endpoints)

### models.py
**Responsibilities:**
- Define request/response schemas
- Validate API inputs
- Serialize API outputs
- Type safety for FastAPI

**Used by:** `main.py` (endpoint signatures)

### config.py
**Responsibilities:**
- Load environment variables
- Provide default values
- Centralize configuration
- Type conversion for settings

**Used by:** All modules

## 📦 Database Schema Details

### sessions table
```sql
CREATE TABLE sessions (
    session_id VARCHAR PRIMARY KEY,
    created_at DATETIME,
    updated_at DATETIME
);
```

### messages table
```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id VARCHAR NOT NULL,
    role VARCHAR NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    citations TEXT,         -- JSON array
    created_at DATETIME
);

CREATE INDEX idx_session ON messages(session_id);
```

### feedback table
```sql
CREATE TABLE feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id VARCHAR NOT NULL,
    message_id INTEGER NOT NULL,
    rating INTEGER NOT NULL,  -- 1 or -1
    note TEXT,
    created_at DATETIME
);

CREATE INDEX idx_session ON feedback(session_id);
CREATE INDEX idx_message ON feedback(message_id);
```

## 🔐 Security Considerations

### Current Implementation
- ✅ CORS protection (configured origins)
- ✅ Input validation (Pydantic models)
- ✅ SQL injection prevention (SQLAlchemy ORM)
- ✅ Environment variable configuration

### Recommended for Production
- 🔒 Add API authentication (API keys, JWT)
- 🔒 Rate limiting per user/session
- 🔒 Admin endpoint authentication
- 🔒 HTTPS/TLS encryption
- 🔒 Input sanitization for notes/messages
- 🔒 Database backups
- 🔒 Logging and monitoring

## 📈 Scalability Considerations

### Current Setup (Good for < 100 concurrent users)
- SQLite database (single file)
- Synchronous OpenAI calls
- In-process ChromaDB

### For Larger Scale
- Migrate to PostgreSQL/MySQL
- Add caching layer (Redis)
- Queue background tasks (Celery)
- Use async/await for API calls
- Deploy ChromaDB as separate service
- Load balancing with multiple workers
- Horizontal scaling with containers

## 🎯 Key Design Decisions

1. **Session Management in Frontend**: UUID generation in Next.js allows offline session creation
2. **SQLite for Persistence**: Simple, zero-config, file-based storage suitable for initial deployment
3. **ChromaDB**: Open-source, easy to use, supports metadata filtering
4. **OpenAI Embeddings**: High quality, same provider as LLM, consistent results
5. **RAG Pattern**: Grounds responses in actual course catalog data
6. **Conversation History**: Last 6 messages provide context without token waste
7. **Citations as JSON**: Flexible schema, easy to extend with metadata

---

This architecture provides a solid foundation for the OIRA chatbot while remaining simple enough to understand, deploy, and maintain.
