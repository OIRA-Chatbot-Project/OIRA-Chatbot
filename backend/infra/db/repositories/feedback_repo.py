"""Repository for feedback operations."""
from sqlalchemy.orm import Session as DBSession_type
from infra.db.models import Feedback as DBFeedback


class FeedbackRepository:
    def __init__(self, db: DBSession_type):
        self.db = db

    def add_feedback(self, session_id: str, message_id: int, rating: int, note: str = None) -> DBFeedback:
        fb = DBFeedback(session_id=session_id, message_id=message_id, rating=rating, note=note)
        self.db.add(fb)
        self.db.commit()
        self.db.refresh(fb)
        return fb

    def delete_feedback_for_messages(self, message_ids: list):
        if message_ids:
            self.db.query(DBFeedback).filter(DBFeedback.message_id.in_(message_ids)).delete(synchronize_session=False)
