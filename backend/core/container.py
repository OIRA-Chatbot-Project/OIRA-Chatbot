"""Dependency injection / composition root."""
from __future__ import annotations
from typing import Optional

_chatbot_service_instance: Optional[object] = None


def get_chatbot_service():
    """Get or create the global ChatbotService singleton."""
    global _chatbot_service_instance
    if _chatbot_service_instance is None:
        from domain.services.chat_service import ChatbotService
        _chatbot_service_instance = ChatbotService()
    return _chatbot_service_instance
