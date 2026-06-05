from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session as SASession
from sqlalchemy import func

from app.data.models.session import Session
from app.data.models.message import Message


class SQLSessionRepository:
    def __init__(self, db: SASession) -> None:
        self.db = db

    def get_by_id(self, session_id: str) -> Optional[Session]:
        return self.db.query(Session).filter(Session.session_id == session_id).first()

    def get_by_id_and_user(self, session_id: str, user_id: int) -> Optional[Session]:
        return self.db.query(Session).filter(
            Session.session_id == session_id,
            Session.user_id == user_id,
        ).first()

    def list_for_user_with_message_counts(self, user_id: int) -> List:
        """Returns rows of (session_id, title, created_at, updated_at, message_count)."""
        return (
            self.db.query(
                Session.session_id,
                Session.title,
                Session.created_at,
                Session.updated_at,
                func.count(Message.id).label("message_count"),
            )
            .outerjoin(Message, Message.session_id == Session.session_id)
            .filter(Session.user_id == user_id)
            .group_by(
                Session.session_id,
                Session.title,
                Session.created_at,
                Session.updated_at,
            )
            .order_by(Session.updated_at.desc())
            .all()
        )

    def get_or_create_for_user(self, session_id: str, user_id: int) -> Session:
        """Return existing session (verifying ownership) or create a new one."""
        from fastapi import HTTPException

        session = self.get_by_id(session_id)
        if not session:
            return self.create(session_id=session_id, user_id=user_id)
        if session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Session does not belong to user")
        self.touch(session)
        return session

    def create(self, session_id: str, user_id: int) -> Session:
        session = Session(session_id=session_id, user_id=user_id)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def update(self, session: Session) -> Session:
        self.db.commit()
        self.db.refresh(session)
        return session

    def touch(self, session: Session) -> None:
        """Update the updated_at timestamp."""
        session.updated_at = (
            datetime.now(datetime.UTC)  # type: ignore
            if hasattr(datetime, "UTC")
            else datetime.utcnow()
        )
        self.db.commit()

    def delete(self, session: Session) -> None:
        """Delete a session and all its messages (manual cascade)."""
        self.db.query(Message).filter(
            Message.session_id == session.session_id
        ).delete(synchronize_session=False)
        self.db.delete(session)
        self.db.commit()
