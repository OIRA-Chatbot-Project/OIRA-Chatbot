from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db, Session as DBSession, User as DBUser, Message as DBMessage, Feedback as DBFeedback
from models import FeedbackRequest, FeedbackResponse
from auth import get_current_user
from utils import get_user_from_token, get_session_for_user

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit feedback for an assistant message

    - Accepts thumbs up (1) or thumbs down (-1) rating
    - Optional note for additional feedback
    - Stores feedback in database for analytics
    """
    try:
        user = get_user_from_token(db, current_user)

        # Verify session belongs to user
        get_session_for_user(db, request.session_id, user)
        
        # Validate that the message exists and belongs to the session
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
        
        # Validate rating
        if request.rating not in [1, -1]:
            raise HTTPException(
                status_code=400,
                detail="Rating must be 1 (thumbs up) or -1 (thumbs down)"
            )
        
        # Create feedback record
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
