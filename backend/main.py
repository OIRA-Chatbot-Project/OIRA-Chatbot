from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config
from database import init_db, engine
from models import HealthResponse
from chatbot_service import get_chatbot_service

# Import route modules
from routes import users, sessions, messages, chat, feedback, schedule, admin


def migrate_database():
    """Run database migrations to add new columns if they don't exist."""
    from sqlalchemy import text, inspect

    try:
        with engine.connect() as conn:
            inspector = inspect(engine)

            # Check if messages table exists
            if 'messages' not in inspector.get_table_names():
                print("Messages table does not exist yet, skipping migration")
                return

            columns = [col['name'] for col in inspector.get_columns('messages')]

            # Add follow_ups column if it doesn't exist
            if 'follow_ups' not in columns:
                print("Adding 'follow_ups' column to messages table...")
                conn.execute(text("ALTER TABLE messages ADD COLUMN follow_ups TEXT"))
                conn.commit()
                print("Migration complete: 'follow_ups' column added")
            else:
                print("Database schema is up to date")
    except Exception as e:
        print(f"Migration warning: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    init_db()
    print("Database initialized successfully")

    # Run migrations
    migrate_database()

    # Pre-warm chatbot service to avoid cold start latency on first request
    get_chatbot_service()
    print("Chatbot service initialized successfully")

    yield

    # Shutdown (if needed)
    print("Shutting down...")


# Initialize FastAPI app with lifespan
app = FastAPI(
    title=config.API_TITLE,
    description=config.API_DESCRIPTION,
    version=config.API_VERSION,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        version=config.API_VERSION
    )


# Include all routers
app.include_router(users.router)
app.include_router(sessions.router)
app.include_router(messages.router)
app.include_router(chat.router)
app.include_router(feedback.router)
app.include_router(schedule.router)
app.include_router(admin.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
