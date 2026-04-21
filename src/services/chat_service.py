from __future__ import annotations
from src.repository.message_repository import ChatMessageRepository, ChatSessionRepository
from src.repository.orm import ChatMessageRecord, ChatSessionRecord
from src.repository.unit_of_work import UnitOfWork

class ChatHistoryService:
    """Service responsible for session/message persistence operations."""
    def __init__(
        self,
        session_repository: ChatSessionRepository,
        message_repository: ChatMessageRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self.session_repository = session_repository
        self.message_repository = message_repository
        self.unit_of_work = unit_of_work

    def create_session(self, user_id: str, title: str) -> ChatSessionRecord:
        with self.unit_of_work:
            return self._create_session_in_transaction(user_id=user_id, title=title)

    def get_session(self, session_id: str) -> ChatSessionRecord | None:
        raise NotImplementedError("TODO: implement ChatHistoryService.get_session")

    def list_user_sessions(
        self, user_id: str, limit: int = 20, offset: int = 0
    ) -> list[ChatSessionRecord]:
        raise NotImplementedError("TODO: implement ChatHistoryService.list_user_sessions")

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, str] | None = None,
    ) -> ChatMessageRecord:
        with self.unit_of_work:
            return self._append_message_in_transaction(
                session_id=session_id,
                role=role,
                content=content,
                metadata=metadata,
            )

    def list_session_messages(
        self, session_id: str, limit: int = 100, offset: int = 0
    ) -> list[ChatMessageRecord]:
        raise NotImplementedError("TODO: implement ChatHistoryService.list_session_messages")

    def update_message(self, message_id: str, new_content: str) -> ChatMessageRecord:
        with self.unit_of_work:
            return self._update_message_in_transaction(
                message_id=message_id, new_content=new_content
            )

    def _create_session_in_transaction(
        self, user_id: str, title: str
    ) -> ChatSessionRecord:
        raise NotImplementedError(
            "TODO: implement ChatHistoryService._create_session_in_transaction"
        )

    def _append_message_in_transaction(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, str] | None = None,
    ) -> ChatMessageRecord:
        raise NotImplementedError(
            "TODO: implement ChatHistoryService._append_message_in_transaction"
        )

    def _update_message_in_transaction(
        self, message_id: str, new_content: str
    ) -> ChatMessageRecord:
        raise NotImplementedError(
            "TODO: implement ChatHistoryService._update_message_in_transaction"
        )


class ChatService(ChatHistoryService):
    """Backward-compatible alias for older chat service imports."""
