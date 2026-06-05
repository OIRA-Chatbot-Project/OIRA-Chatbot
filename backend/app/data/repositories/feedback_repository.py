from typing import Optional, List
from sqlalchemy.orm import Session as SASession

from app.data.models.feedback import Feedback


class SQLFeedbackRepository:
    def __init__(self, db: SASession) -> None:
        self.db = db

    def create(
        self,
        session_id: str,
        message_id: int,
        rating: int,
        note: Optional[str] = None,
    ) -> Feedback:
        feedback = Feedback(
            session_id=session_id,
            message_id=message_id,
            rating=rating,
            note=note,
        )
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback

    def delete_for_messages(self, message_ids: List[int]) -> None:
        if message_ids:
            self.db.query(Feedback).filter(
                Feedback.message_id.in_(message_ids)
            ).delete(synchronize_session=False)
            self.db.commit()
