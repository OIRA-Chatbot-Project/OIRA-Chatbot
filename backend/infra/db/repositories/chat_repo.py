"""Repository for chat session operations."""
from sqlalchemy.orm import Session as DBSession_type
from infra.db.models import Session as DBSession, User as DBUser


class ChatRepository:
    def __init__(self, db: DBSession_type):
        self.db = db

    def get_session(self, session_id: str):
        return self.db.query(DBSession).filter(DBSession.session_id == session_id).first()

    def get_or_create_session(self, session_id: str, user_id: int) -> DBSession:
        session = self.get_session(session_id)
        if not session:
            session = DBSession(session_id=session_id, user_id=user_id)
            self.db.add(session)
            self.db.commit()
        return session

    def verify_session_owner(self, session_id: str, user_id: int) -> bool:
        session = self.get_session(session_id)
        return session is not None and session.user_id == user_id

    def get_user_by_clerk_id(self, clerk_user_id: str):
        return self.db.query(DBUser).filter(DBUser.clerk_user_id == clerk_user_id).first()
