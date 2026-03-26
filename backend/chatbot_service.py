"""
Backward-compatible shim - imports from domain/services/chat_service.py and core/container.py.
"""
from domain.services.chat_service import ChatbotService
from core.container import get_chatbot_service

__all__ = ["ChatbotService", "get_chatbot_service"]
