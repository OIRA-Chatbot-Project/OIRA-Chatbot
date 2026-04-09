"""
SessionService: session lifecycle + LLM title generation.
"""
from typing import List, Optional

from app.data.repositories.session_repository import SQLSessionRepository
from app.data.models.session import Session
from app.api.schemas.session import SessionInfo


class SessionService:
    def __init__(self, session_repo: SQLSessionRepository, llm_client) -> None:
        self.session_repo = session_repo
        self.llm = llm_client

    def get_sessions_for_user(self, user_id: int) -> List[SessionInfo]:
        rows = self.session_repo.list_for_user_with_message_counts(user_id)
        return [
            SessionInfo(
                session_id=r.session_id,
                title=r.title,
                created_at=r.created_at,
                updated_at=r.updated_at,
                has_messages=r.message_count > 0,
            )
            for r in rows
            if r.message_count > 0
        ]

    def get_or_create(self, session_id: str, user_id: int) -> Session:
        from fastapi import HTTPException

        session = self.session_repo.get_by_id(session_id)
        if not session:
            return self.session_repo.create(session_id=session_id, user_id=user_id)

        if session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Session does not belong to user")

        self.session_repo.touch(session)
        return session

    def require_owned_by(self, session_id: str, user_id: int) -> Session:
        from fastapi import HTTPException

        session = self.session_repo.get_by_id_and_user(session_id, user_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session

    def delete(self, session_id: str, user_id: int) -> None:
        session = self.require_owned_by(session_id, user_id)
        self.session_repo.delete(session)

    def generate_title(self, session_id: str, user_id: int, first_message: str) -> str:
        session = self.require_owned_by(session_id, user_id)

        prompt = (
            f'Generate a concise, descriptive title (3-5 words maximum) for a chat '
            f'conversation that starts with this message:\n\n"{first_message}"\n\n'
            "Requirements:\n"
            "- Keep it under 50 characters\n"
            "- Make it descriptive but concise\n"
            "- Use title case\n"
            "- No quotes or special formatting\n"
            '- Example: "Computer Science Requirements" or "CSCI 204 Prerequisites"\n\n'
            "Title:"
        )
        response = self.llm.invoke(prompt)
        title = response.content.strip().replace('"', "").replace("'", "").strip()
        if len(title) > 60:
            title = title[:57] + "..."

        session.title = title
        self.session_repo.update(session)
        return title

    def update_title(self, session_id: str, user_id: int, title: str) -> None:
        from fastapi import HTTPException

        if not title.strip():
            raise HTTPException(status_code=400, detail="Title cannot be empty")
        session = self.require_owned_by(session_id, user_id)
        session.title = title.strip()
        self.session_repo.update(session)

    def set_summary(self, session_id: str, summary: str) -> None:
        session = self.session_repo.get_by_id(session_id)
        if session:
            session.conversation_summary = summary
            self.session_repo.update(session)
