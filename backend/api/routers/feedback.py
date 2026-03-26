"""
Feedback management routes.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from infra.db.engine import get_db
from infra.db.models import Session as DBSession, User as DBUser, Message as DBMessage, Feedback as DBFeedback
from api.schemas import FeedbackRequest, FeedbackResponse
from auth import get_current_user, get_user_id_from_token

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit feedback for an assistant message."""
    try:
        clerk_user_id = get_user_id_from_token(current_user)

        user = db.query(DBUser).filter(DBUser.clerk_user_id == clerk_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        session = db.query(DBSession).filter(
            DBSession.session_id == request.session_id,
            DBSession.user_id == user.id
        ).first()

        if not session:
            raise HTTPException(status_code=403, detail="Session does not belong to user")

        message = db.query(DBMessage).filter(
            DBMessage.id == request.message_id,
            DBMessage.session_id == request.session_id,
            DBMessage.role == "assistant"
        ).first()

        if not message:
            raise HTTPException(
                status_code=404,
                detail="Message not found or does not belong to this session"
            )

        if request.rating not in [1, -1]:
            raise HTTPException(
                status_code=400,
                detail="Rating must be 1 (thumbs up) or -1 (thumbs down)"
            )

        feedback = DBFeedback(
            session_id=request.session_id,
            message_id=request.message_id,
            rating=request.rating,
            note=request.note
        )
        db.add(feedback)
        db.commit()
        db.refresh(feedback)

        return FeedbackResponse(
            success=True,
            feedback_id=feedback.id
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error submitting feedback: {str(e)}")
