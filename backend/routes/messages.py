from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json

from database import get_db, Session as DBSession, User as DBUser, Message as DBMessage
from models import MessagesResponse, MessageResponse, Citation
from auth import get_current_user
from utils import get_user_from_token
from logger import get_logger

logger = get_logger(__name__)

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
        user = get_user_from_token(db, current_user)

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
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse citations for message {msg.id}")
            
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
