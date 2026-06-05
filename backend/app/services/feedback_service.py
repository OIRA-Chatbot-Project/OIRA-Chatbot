"""
FeedbackService: feedback submission and validation.
"""
from fastapi import HTTPException

from app.data.repositories.feedback_repository import SQLFeedbackRepository
from app.data.repositories.session_repository import SQLSessionRepository
from app.data.repositories.message_repository import SQLMessageRepository
from app.data.repositories.user_repository import SQLUserRepository
from app.data.models.feedback import Feedback


class FeedbackService:
    def __init__(
        self,
        feedback_repo: SQLFeedbackRepository,
        session_repo: SQLSessionRepository,
        message_repo: SQLMessageRepository,
    ) -> None:
        self.feedback_repo = feedback_repo
        self.session_repo = session_repo
        self.message_repo = message_repo

    def submit(
        self,
        clerk_user_id: str,
        session_id: str,
        message_id: int,
        rating: int,
        note: str | None,
        user_repo: SQLUserRepository,
    ) -> Feedback:
        user = user_repo.get_by_clerk_id(clerk_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        session = self.session_repo.get_by_id_and_user(session_id, user.id)
        if not session:
            raise HTTPException(status_code=403, detail="Session does not belong to user")

        message = self.message_repo.get_by_id(message_id)
        if not message or message.session_id != session_id or message.role != "assistant":
            raise HTTPException(
                status_code=404,
                detail="Message not found or does not belong to this session",
            )

        if rating not in (1, -1):
            raise HTTPException(
                status_code=400,
                detail="Rating must be 1 (thumbs up) or -1 (thumbs down)",
            )

        return self.feedback_repo.create(
            session_id=session_id,
            message_id=message_id,
            rating=rating,
            note=note,
        )
