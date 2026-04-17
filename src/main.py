 
from __future__ import annotations
from fastapi import FastAPI
from src.api_endpoints import api_router

def create_app() -> FastAPI:
    """Application factory for the advising API."""
    app = FastAPI(
        title="OIRA Student Advising API",
        description="Grounded AI advising API powered by course catalog knowledge.",
        version="0.1.0",
    )
    app.include_router(api_router)

    @app.get("/health", tags=["health"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return app

app = create_app()