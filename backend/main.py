from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import json
from datetime import datetime

import config
from database import get_db, init_db, Session as DBSession, Message as DBMessage, Feedback as DBFeedback
from models import (
    ChatRequest, ChatResponse, Citation,
    FeedbackRequest, FeedbackResponse,
    MessagesResponse, MessageResponse,
    HealthResponse
)
from chatbot_service import chatbot_service

# Initialize FastAPI app
app = FastAPI(
    title=config.API_TITLE,
    description=config.API_DESCRIPTION,
    version=config.API_VERSION
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup"""
    init_db()
    print("Database initialized successfully")


@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        version=config.API_VERSION
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
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
        # Ensure session exists
        session = db.query(DBSession).filter(DBSession.session_id == request.session_id).first()
        if not session:
            session = DBSession(session_id=request.session_id)
            db.add(session)
            db.commit()
        else:
            # Update session timestamp
            session.updated_at = datetime.utcnow()
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
        
        # Get answer from chatbot service
        answer, citations = chatbot_service.get_answer(request.message, conversation_history)
        
        # Log assistant's response
        assistant_message = DBMessage(
            session_id=request.session_id,
            role="assistant",
            content=answer,
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
            session_id=request.session_id
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")


@app.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest, db: Session = Depends(get_db)):
    """
    Submit feedback for an assistant message
    
    - Accepts thumbs up (1) or thumbs down (-1) rating
    - Optional note for additional feedback
    - Stores feedback in database for analytics
    """
    try:
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


@app.get("/messages", response_model=MessagesResponse)
async def get_messages(session_id: str, db: Session = Depends(get_db)):
    """
    Retrieve all messages for a given session
    
    - Returns full conversation history
    - Includes citations for assistant messages
    - Used to restore chat history when user returns
    """
    try:
        # Verify session exists
        session = db.query(DBSession).filter(DBSession.session_id == session_id).first()
        if not session:
            # Return empty history for non-existent sessions (not an error)
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


# Optional: Admin endpoint for triggering re-ingestion
@app.post("/admin/ingest")
async def trigger_ingestion():
    """
    Trigger re-ingestion of PDFs from data/ folder
    
    Note: This is a placeholder. In production, you might want to:
    - Add authentication/authorization
    - Run ingestion in background task
    - Return job status
    """
    try:
        # Import and run ingestion script
        import subprocess
        result = subprocess.run(
            ["python", "ingest_database.py"],
            capture_output=True,
            text=True,
            cwd="."
        )
        
        if result.returncode == 0:
            return {"success": True, "message": "Ingestion completed successfully"}
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Ingestion failed: {result.stderr}"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error triggering ingestion: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
