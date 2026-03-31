"""
Main application entry point for the OIRA Chatbot API.

This module initializes the FastAPI application, sets up middleware (CORS),
configures database initialization on startup, and includes all application routers.
"""
import sys
import os

# Force UTF-8 encoding for stdout/stderr on Windows to prevent
# 'charmap' codec errors when printing Unicode characters from LLM output
if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core import config
from core.database import init_db
from core.models import HealthResponse

# Import route modules
from routes import users, sessions, messages, chat, feedback, schedule, admin

# Initialize FastAPI app
app = FastAPI(
    title=config.API_TITLE,
    description=config.API_DESCRIPTION,
    version=config.API_VERSION
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup.

    This function is called when the application starts. It triggers the
    creation of all database tables defined in the SQLAlchemy models.
    """
    init_db()
    print("Database initialized successfully")


@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint.

    Returns:
        HealthResponse: A response object containing the status and version of the API.
    """
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
    uvicorn.run(app, host="127.0.0.1", port=8000)
