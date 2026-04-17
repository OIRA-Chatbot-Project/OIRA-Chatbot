from fastapi import APIRouter
from src.api_endpoints.chat import router as chat_router
from src.api_endpoints.document import router as document_router
from src.api_endpoints.user import router as user_router

api_router = APIRouter()
api_router.include_router(chat_router)
api_router.include_router(document_router)
api_router.include_router(user_router)

__all__ = ["api_router"]
