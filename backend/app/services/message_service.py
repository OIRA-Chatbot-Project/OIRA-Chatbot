"""
MessageService: message retrieval, creation, editing.
"""
import json
from dataclasses import dataclass, field
from typing import List, Optional

from app.data.repositories.message_repository import SQLMessageRepository
from app.data.repositories.feedback_repository import SQLFeedbackRepository
from app.data.repositories.session_repository import SQLSessionRepository
from app.data.models.message import Message
from app.api.schemas.chat import Citation
from app.api.schemas.message import MessageResponse


@dataclass
class EditResult:
    success: bool
    deleted_message_ids: List[int] = field(default_factory=list)


class MessageService:
    def __init__(
        self,
        message_repo: SQLMessageRepository,
        feedback_repo: SQLFeedbackRepository,
    ) -> None:
        self.message_repo = message_repo
        self.feedback_repo = feedback_repo

    def get_for_session(
        self,
        session_id: str,
        user_id: int,
        session_repo: SQLSessionRepository,
    ) -> List[MessageResponse]:
        """Return all messages for a session, verifying ownership."""
        session = session_repo.get_by_id_and_user(session_id, user_id)
        if not session:
            return []

        messages = self.message_repo.get_for_session(session_id)
        responses = []
        for msg in messages:
            citations = None
            if msg.citations:
                try:
                    data = json.loads(msg.citations)
                    citations = [Citation(**c) for c in data]
                except Exception:
                    pass
            responses.append(
                MessageResponse(
                    id=msg.id,
                    role=msg.role,
                    content=msg.content,
                    citations=citations,
                    created_at=msg.created_at,
                )
            )
        return responses

    def save_user_message(self, session_id: str, content: str) -> Message:
        return self.message_repo.create(session_id=session_id, role="user", content=content)

    def save_assistant_message(
        self,
        session_id: str,
        content: str,
        citations: List[dict],
    ) -> Message:
        return self.message_repo.create(
            session_id=session_id,
            role="assistant",
            content=content,
            citations=json.dumps(citations),
        )

    def get_history(
        self, session_id: str, before_id: int, limit: int = 6
    ) -> List[dict]:
        """Return last `limit` messages before `before_id`, chronological order."""
        msgs = self.message_repo.get_history_before(session_id, before_id, limit)
        return [{"role": m.role, "content": m.content} for m in msgs]

    def edit_message(
        self,
        message_id: int,
        session_id: str,
        user_id: int,
        new_content: str,
        session_repo: SQLSessionRepository,
    ) -> EditResult:
        from fastapi import HTTPException
        from datetime import datetime

        session = session_repo.get_by_id_and_user(session_id, user_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        message = self.message_repo.get_by_id(message_id)
        if not message or message.session_id != session_id:
            raise HTTPException(status_code=404, detail="Message not found")
        if message.role != "user":
            raise HTTPException(status_code=400, detail="Only user messages can be edited")

        message.content = new_content
        deleted_ids = self.message_repo.delete_after(session_id, message_id)
        if deleted_ids:
            self.feedback_repo.delete_for_messages(deleted_ids)

        session.updated_at = (
            datetime.now(datetime.UTC)  # type: ignore
            if hasattr(datetime, "UTC")
            else datetime.utcnow()
        )
        session_repo.update(session)
        self.message_repo.update(message)
        return EditResult(success=True, deleted_message_ids=deleted_ids)

    def delete_after(self, session_id: str, after_id: int) -> List[int]:
        """Delete messages after `after_id`, cascade feedback. Returns deleted ids."""
        deleted_ids = self.message_repo.delete_after(session_id, after_id)
        if deleted_ids:
            self.feedback_repo.delete_for_messages(deleted_ids)
        return deleted_ids
