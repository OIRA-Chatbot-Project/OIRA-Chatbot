from typing import Optional, List
from sqlalchemy.orm import Session as SASession

from app.data.models.message import Message


class SQLMessageRepository:
    def __init__(self, db: SASession) -> None:
        self.db = db

    def get_for_session(self, session_id: str) -> List[Message]:
        return (
            self.db.query(Message)
            .filter(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
            .all()
        )

    def get_history_before(self, session_id: str, before_id: int, limit: int) -> List[Message]:
        """Return up to `limit` messages before `before_id`, in ascending order."""
        rows = (
            self.db.query(Message)
            .filter(
                Message.session_id == session_id,
                Message.id < before_id,
            )
            .order_by(Message.id.desc())
            .limit(limit)
            .all()
        )
        return list(reversed(rows))

    def get_by_id(self, message_id: int) -> Optional[Message]:
        return self.db.query(Message).filter(Message.id == message_id).first()

    def count_for_session(self, session_id: str) -> int:
        return self.db.query(Message).filter(Message.session_id == session_id).count()

    def get_older_than_window(self, session_id: str, keep_count: int) -> List[Message]:
        """Return messages that fall outside the most-recent `keep_count` window."""
        recent_ids = (
            self.db.query(Message.id)
            .filter(Message.session_id == session_id)
            .order_by(Message.id.desc())
            .limit(keep_count)
            .subquery()
        )
        return (
            self.db.query(Message)
            .filter(
                Message.session_id == session_id,
                ~Message.id.in_(recent_ids),
            )
            .order_by(Message.id.asc())
            .all()
        )

    def create(
        self,
        session_id: str,
        role: str,
        content: str,
        citations: Optional[str] = None,
    ) -> Message:
        msg = Message(
            session_id=session_id,
            role=role,
            content=content,
            citations=citations,
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def update(self, message: Message) -> Message:
        self.db.commit()
        self.db.refresh(message)
        return message

    def delete_after(self, session_id: str, after_id: int) -> List[int]:
        """Delete all messages in the session with id > after_id; return deleted ids."""
        ids = [
            mid
            for (mid,) in self.db.query(Message.id)
            .filter(
                Message.session_id == session_id,
                Message.id > after_id,
            )
            .all()
        ]
        if ids:
            self.db.query(Message).filter(Message.id.in_(ids)).delete(
                synchronize_session=False
            )
            self.db.commit()
        return ids
