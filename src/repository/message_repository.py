from __future__ import annotations
from src.repository.abstract_repository import BaseRepository
from src.repository.orm import ChatMessageRecord, ChatSessionRecord

class ChatSessionRepository(BaseRepository[ChatSessionRecord, str]):
    """Repository for chat session metadata."""
    def create(self, entity: ChatSessionRecord) -> ChatSessionRecord:
        raise NotImplementedError("TODO: implement ChatSessionRepository.create")

    def get_by_id(self, entity_id: str) -> ChatSessionRecord | None:
        raise NotImplementedError("TODO: implement ChatSessionRepository.get_by_id")

    def update(self, entity: ChatSessionRecord) -> ChatSessionRecord:
        raise NotImplementedError("TODO: implement ChatSessionRepository.update")

    def delete(self, entity_id: str) -> None:
        raise NotImplementedError("TODO: implement ChatSessionRepository.delete")

    def list(self, limit: int = 100, offset: int = 0) -> list[ChatSessionRecord]:
        raise NotImplementedError("TODO: implement ChatSessionRepository.list")

    def list_sessions_by_user(
        self, user_id: str, limit: int = 20, offset: int = 0
    ) -> list[ChatSessionRecord]:
        """Return a user's chat sessions ordered by recency."""
        raise NotImplementedError(
            "TODO: implement ChatSessionRepository.list_sessions_by_user"
        )

class ChatMessageRepository(BaseRepository[ChatMessageRecord, str]):
    """Repository for individual chat messages."""
    def create(self, entity: ChatMessageRecord) -> ChatMessageRecord:
        raise NotImplementedError("TODO: implement ChatMessageRepository.create")

    def get_by_id(self, entity_id: str) -> ChatMessageRecord | None:
        raise NotImplementedError("TODO: implement ChatMessageRepository.get_by_id")

    def update(self, entity: ChatMessageRecord) -> ChatMessageRecord:
        raise NotImplementedError("TODO: implement ChatMessageRepository.update")

    def delete(self, entity_id: str) -> None:
        raise NotImplementedError("TODO: implement ChatMessageRepository.delete")

    def list(self, limit: int = 100, offset: int = 0) -> list[ChatMessageRecord]:
        raise NotImplementedError("TODO: implement ChatMessageRepository.list")

    def list_messages_by_session(
        self, session_id: str, limit: int = 100, offset: int = 0
    ) -> list[ChatMessageRecord]:
        """Return session messages in chronological order."""
        raise NotImplementedError(
            "TODO: implement ChatMessageRepository.list_messages_by_session"
        )