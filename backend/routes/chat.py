from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import re
import json
from datetime import datetime

from database import get_db, Session as DBSession, User as DBUser, Message as DBMessage
from models import ChatRequest, ChatResponse, Citation
from auth import get_current_user, get_user_id_from_token
from chatbot_service import get_chatbot_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process a chat message and return an answer with citations
    
    - Creates a session if it doesn't exist
    - Logs the user's message
    - Retrieves relevant information from ChromaDB
    - Generates an answer using OpenAI
    - Logs the assistant's response with citations
    - Returns the answer and message ID
    """
    try:
        # Get user ID from token
        clerk_user_id = get_user_id_from_token(current_user)
        
        # Get or create user in database
        user = db.query(DBUser).filter(DBUser.clerk_user_id == clerk_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found. Please sign up first.")
        
        # Ensure session exists and belongs to user
        session = db.query(DBSession).filter(DBSession.session_id == request.session_id).first()
        if not session:
            session = DBSession(session_id=request.session_id, user_id=user.id)
            db.add(session)
            db.commit()
        else:
            # Verify session belongs to user
            if session.user_id != user.id:
                raise HTTPException(status_code=403, detail="Session does not belong to user")
            # Update session timestamp
            session.updated_at = datetime.now(datetime.UTC) if hasattr(datetime, 'UTC') else datetime.utcnow()
            db.commit()
        
        # Log user's message
        user_message = DBMessage(
            session_id=request.session_id,
            role="user",
            content=request.message
        )
        db.add(user_message)
        db.commit()
        
        # Get conversation history for context
        history_messages = db.query(DBMessage).filter(
            DBMessage.session_id == request.session_id,
            DBMessage.id < user_message.id  # Messages before the current one
        ).order_by(DBMessage.created_at.desc()).limit(6).all()
        
        # Convert to format expected by chatbot service
        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in reversed(history_messages)  # Reverse to get chronological order
        ]
        
        # Get answer from chatbot service (now returns 3 values)
        chatbot = get_chatbot_service()
        answer, citations, question_category = chatbot.get_answer(request.message, conversation_history)
        
        # Remove inline bracket citations like "[filename, p. 123]" from the answer
        try:
            cleaned_answer = re.sub(r"\[[^\]]+?,\s*p\.\s*\d+\]", "", answer)
            # Collapse excessive blank lines but preserve markdown line breaks
            cleaned_answer = re.sub(r"\n{3,}", "\n\n", cleaned_answer)
            # Collapse only repeated spaces/tabs (not newlines) to avoid flattening lists
            cleaned_answer = re.sub(r"[ \t]{2,}", " ", cleaned_answer)
            cleaned_answer = cleaned_answer.strip()
        except Exception:
            cleaned_answer = answer

        assistant_message = DBMessage(
            session_id=request.session_id,
            role='assistant',
            content=cleaned_answer,
            citations=json.dumps(citations)  # Store citations as JSON string
        )
        db.add(assistant_message)
        db.commit()
        db.refresh(assistant_message)
        
        # Convert citations to response model
        citation_objects = [Citation(**c) for c in citations]

        return ChatResponse(
            message_id=assistant_message.id,
            answer=answer,
            citations=citation_objects,
            session_id=request.session_id,
            question_category=question_category
        )
        
    except Exception as e:
        db.rollback()
        print(f"ERROR in /chat endpoint: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")
