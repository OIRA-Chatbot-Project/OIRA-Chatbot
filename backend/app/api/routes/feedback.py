"""Feedback submission routes."""
from fastapi import APIRouter, Depends

from app.api.deps import get_feedback_service, get_user_repo
from app.api.schemas.feedback import FeedbackRequest, FeedbackResponse
from app.core.auth import get_current_user, get_user_id_from_token
from app.data.repositories.user_repository import SQLUserRepository
from app.services.feedback_service import FeedbackService

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    current_user: dict = Depends(get_current_user),
    feedback_service: FeedbackService = Depends(get_feedback_service),
    user_repo: SQLUserRepository = Depends(get_user_repo),
):
    """Submit feedback for an assistant message."""
    clerk_user_id = get_user_id_from_token(current_user)
    feedback = feedback_service.submit(
        clerk_user_id=clerk_user_id,
        session_id=request.session_id,
        message_id=request.message_id,
        rating=request.rating,
        note=request.note,
        user_repo=user_repo,
    )
    return FeedbackResponse(success=True, feedback_id=feedback.id)
