"""
Main application entry point for the OIRA Chatbot API.
"""
import sys
import os

if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.settings import settings
from infra.db.engine import init_db
from api.schemas import HealthResponse


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app.API_TITLE,
        description=settings.app.API_DESCRIPTION,
        version=settings.app.API_VERSION,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.app.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def startup_event():
        init_db()
        print("Database initialized successfully")

    @app.get("/", response_model=HealthResponse)
    async def root():
        return HealthResponse(status="healthy", version=settings.app.API_VERSION)

    from api.routers import users, sessions, messages, chat, feedback, schedule, admin
    app.include_router(users.router)
    app.include_router(sessions.router)
    app.include_router(messages.router)
    app.include_router(chat.router)
    app.include_router(feedback.router)
    app.include_router(schedule.router)
    app.include_router(admin.router)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
