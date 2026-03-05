from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json
from datetime import datetime

from database import get_db, Session as DBSession, User as DBUser, Message as DBMessage, Feedback as DBFeedback
from models import MessagesResponse, MessageResponse, Citation, EditMessageRequest, EditMessageResponse
from auth import get_current_user, get_user_id_from_token

router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("", response_model=MessagesResponse)
async def get_messages(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve all messages for a given session
    
    - Returns full conversation history
    - Includes citations for assistant messages
    - Used to restore chat history when user returns
    """
    try:
        # Get user ID from token
        clerk_user_id = get_user_id_from_token(current_user)
        
        # Get user from database
        user = db.query(DBUser).filter(DBUser.clerk_user_id == clerk_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Verify session exists and belongs to user
        session = db.query(DBSession).filter(
            DBSession.session_id == session_id,
            DBSession.user_id == user.id
        ).first()
        
        if not session:
            # Return empty history for non-existent or unauthorized sessions
            return MessagesResponse(
                session_id=session_id,
                messages=[]
            )
        
        # Get all messages for the session
        messages = db.query(DBMessage).filter(
            DBMessage.session_id == session_id
        ).order_by(DBMessage.created_at.asc()).all()
        
        # Convert to response model
        message_responses = []
        for msg in messages:
            citations = None
            if msg.citations:
                try:
                    citation_data = json.loads(msg.citations)
                    citations = [Citation(**c) for c in citation_data]
                except:
                    pass  # If citation parsing fails, leave as None
            
            message_responses.append(MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                citations=citations,
                created_at=msg.created_at
            ))
        
        return MessagesResponse(
            session_id=session_id,
            messages=message_responses
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving messages: {str(e)}")


@router.post("/edit", response_model=EditMessageResponse)
async def edit_message(
    request: EditMessageRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Edit a user message and remove any subsequent messages.
    """
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
            raise HTTPException(status_code=404, detail="Session not found")

        message = db.query(DBMessage).filter(
            DBMessage.id == request.message_id,
            DBMessage.session_id == request.session_id
        ).first()
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        if message.role != "user":
            raise HTTPException(status_code=400, detail="Only user messages can be edited")

        message.content = request.content

        delete_ids = [
            mid for (mid,) in db.query(DBMessage.id).filter(
                DBMessage.session_id == request.session_id,
                DBMessage.id > request.message_id
            ).all()
        ]

        if delete_ids:
            db.query(DBFeedback).filter(DBFeedback.message_id.in_(delete_ids)).delete(synchronize_session=False)
            db.query(DBMessage).filter(DBMessage.id.in_(delete_ids)).delete(synchronize_session=False)

        session.updated_at = datetime.now(datetime.UTC) if hasattr(datetime, 'UTC') else datetime.utcnow()

        db.commit()
        return EditMessageResponse(success=True, deleted_message_ids=delete_ids)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error editing message: {str(e)}")
