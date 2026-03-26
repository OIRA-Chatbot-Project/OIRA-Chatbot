"""Repository for message operations."""
from sqlalchemy.orm import Session as DBSession_type
from infra.db.models import Message as DBMessage


class MessageRepository:
    def __init__(self, db: DBSession_type):
        self.db = db

    def add_message(self, session_id: str, role: str, content: str, citations: str = None) -> DBMessage:
        msg = DBMessage(session_id=session_id, role=role, content=content, citations=citations)
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def get_messages(self, session_id: str, order_asc: bool = True):
        q = self.db.query(DBMessage).filter(DBMessage.session_id == session_id)
        if order_asc:
            q = q.order_by(DBMessage.created_at.asc())
        else:
            q = q.order_by(DBMessage.created_at.desc())
        return q.all()

    def get_message(self, message_id: int):
        return self.db.query(DBMessage).filter(DBMessage.id == message_id).first()

    def delete_messages_after(self, session_id: str, message_id: int):
        ids = [
            mid for (mid,) in self.db.query(DBMessage.id).filter(
                DBMessage.session_id == session_id,
                DBMessage.id > message_id
            ).all()
        ]
        if ids:
            self.db.query(DBMessage).filter(DBMessage.id.in_(ids)).delete(synchronize_session=False)
        return ids
