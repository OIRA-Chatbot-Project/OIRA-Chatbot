"""OIRA Chatbot API — entry point."""
import sys
import os

# Force UTF-8 on Windows to prevent charmap codec errors from LLM output
if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        
from app.api.schemas.common import HealthResponse
from app.core import config
"""FastAPI application factory."""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core import config
from app.core.exceptions import AppError
from app.data.database import init_db
from app.api.routes import users, sessions, messages, chat, feedback, schedule, admin


def create_app() -> FastAPI:
    app = FastAPI(
        title=config.API_TITLE,
        description=config.API_DESCRIPTION,
        version=config.API_VERSION,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.on_event("startup")
    async def startup_event() -> None:
        init_db()
        print("Database initialized successfully")

    app.include_router(users.router)
    app.include_router(sessions.router)
    app.include_router(messages.router)
    app.include_router(chat.router)
    app.include_router(feedback.router)
    app.include_router(schedule.router)
    app.include_router(admin.router)

    return app

app = create_app()


@app.get("/", response_model=HealthResponse)
async def root():
    return HealthResponse(status="healthy", version=config.API_VERSION)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
