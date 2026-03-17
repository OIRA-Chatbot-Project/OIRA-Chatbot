"""
Feedback management routes.

This module provides API endpoints for submitting user feedback on assistant responses.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db, Session as DBSession, User as DBUser, Message as DBMessage, Feedback as DBFeedback
from models import FeedbackRequest, FeedbackResponse
from auth import get_current_user, get_user_id_from_token

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit feedback for an assistant message.
    
    This endpoint allows users to rate an assistant's response (thumbs up/down)
    and optionally provide a text note. Feedback is stored for analysis.

    Args:
        request: The feedback request containing session ID, message ID, rating, and note.
        current_user: The authenticated user information.
        db: The database session.

    Returns:
        FeedbackResponse: An object indicating success and the ID of the created feedback record.

    Raises:
        HTTPException: If the user, session, or message is not found, or if validation fails.
    """
    try:
        # Get user ID from token
        clerk_user_id = get_user_id_from_token(current_user)
        
        # Get user from database
        user = db.query(DBUser).filter(DBUser.clerk_user_id == clerk_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Verify session belongs to user
        session = db.query(DBSession).filter(
            DBSession.session_id == request.session_id,
            DBSession.user_id == user.id
        ).first()
        
        if not session:
            raise HTTPException(status_code=403, detail="Session does not belong to user")
        
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
