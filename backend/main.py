from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
import re
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
import json
from datetime import datetime

import config
from database import get_db, init_db, Session as DBSession, Message as DBMessage, Feedback as DBFeedback, User as DBUser
from models import (
    ChatRequest, ChatResponse, Citation,
    FeedbackRequest, FeedbackResponse,
    MessagesResponse, MessageResponse,
    HealthResponse, ScheduleUploadResponse, ParsedCourse,
    UserCreate, UserResponse, SessionInfo, SessionsResponse
)
from chatbot_service import chatbot_service
from schedule_parser import extract_text_from_upload, parse_schedule_entries, summarize_schedule
from auth import get_current_user, get_user_id_from_token

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


@app.post("/users", response_model=UserResponse)
async def create_or_get_user(
    user_data: UserCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new user or retrieve existing user
    
    - Checks if user already exists by clerk_user_id
    - Creates new user if doesn't exist
    - Returns user information
    """
    try:
        # Verify the user making request matches the user being created
        clerk_user_id = get_user_id_from_token(current_user)
        if clerk_user_id != user_data.clerk_user_id:
            raise HTTPException(status_code=403, detail="Cannot create user for different clerk_user_id")
        
        # Check if user already exists
        existing_user = db.query(DBUser).filter(
            DBUser.clerk_user_id == user_data.clerk_user_id
        ).first()
        
        if existing_user:
            # Update user info if changed
            if user_data.email != existing_user.email or user_data.name != existing_user.name:
                existing_user.email = user_data.email
                existing_user.name = user_data.name
                existing_user.updated_at = datetime.now(datetime.UTC) if hasattr(datetime, 'UTC') else datetime.utcnow()
                db.commit()
                db.refresh(existing_user)
            
            return UserResponse(
                id=existing_user.id,
                clerk_user_id=existing_user.clerk_user_id,
                email=existing_user.email,
                name=existing_user.name,
                created_at=existing_user.created_at
            )
        
        # Create new user
        new_user = DBUser(
            clerk_user_id=user_data.clerk_user_id,
            email=user_data.email,
            name=user_data.name
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return UserResponse(
            id=new_user.id,
            clerk_user_id=new_user.clerk_user_id,
            email=new_user.email,
            name=new_user.name,
            created_at=new_user.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating/retrieving user: {str(e)}")


@app.post("/chat", response_model=ChatResponse)
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
        
        # Get answer from chatbot service
        answer, citations = chatbot_service.get_answer(request.message, conversation_history)
        
        # Log assistant's response
        # Remove inline bracket citations like "[filename, p. 123]" from the answer
        try:
            cleaned_answer = re.sub(r"\[[^\]]+?,\s*p\.\s*\d+\]", "", answer)
            # collapse multiple spaces/newlines that may have been left behind
            cleaned_answer = re.sub(r"\n{2,}", "\n\n", cleaned_answer)
            cleaned_answer = re.sub(r"\s{2,}", " ", cleaned_answer)
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
            session_id=request.session_id
        )
        
    except Exception as e:
        db.rollback()
        print(f"ERROR in /chat endpoint: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")


@app.get("/sessions")
async def get_sessions(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all sessions for the current user (lightweight, without messages)
    """
    try:
        # Get user ID from token
        clerk_user_id = get_user_id_from_token(current_user)
        
        # Get user from database
        user = db.query(DBUser).filter(DBUser.clerk_user_id == clerk_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get all sessions with message counts (optimized query)
        sessions = db.query(
            DBSession.session_id,
            DBSession.created_at,
            func.count(DBMessage.id).label('message_count')
        ).outerjoin(
            DBMessage, DBMessage.session_id == DBSession.session_id
        ).filter(
            DBSession.user_id == user.id
        ).group_by(
            DBSession.session_id, DBSession.created_at
        ).order_by(
            DBSession.updated_at.desc()
        ).all()
        
        return {
            "sessions": [
                {
                    "session_id": s.session_id,
                    "created_at": s.created_at.isoformat(),
                    "has_messages": s.message_count > 0
                }
                for s in sessions
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching sessions: {str(e)}")


@app.post("/schedule/upload", response_model=ScheduleUploadResponse)
async def upload_schedule(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Accept a screenshot/text export of a student's past schedule, extract the courses,
    and provide tailored recommendations.
    """
    try:
        # Get user ID from token
        clerk_user_id = get_user_id_from_token(current_user)
        
        # Get user from database
        user = db.query(DBUser).filter(DBUser.clerk_user_id == clerk_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found. Please sign up first.")
        
        session = db.query(DBSession).filter(DBSession.session_id == session_id).first()
        if not session:
            session = DBSession(session_id=session_id, user_id=user.id)
            db.add(session)
            db.commit()
        else:
            # Verify session belongs to user
            if session.user_id != user.id:
                raise HTTPException(status_code=403, detail="Session does not belong to user")
            session.updated_at = datetime.now(datetime.UTC) if hasattr(datetime, 'UTC') else datetime.utcnow()
            db.commit()

        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        try:
            raw_text = extract_text_from_upload(contents, file.filename)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        parsed_courses = parse_schedule_entries(raw_text)
        if not parsed_courses:
            raise HTTPException(
                status_code=400,
                detail="Could not detect any courses in the uploaded schedule. Please try a clearer image or a text export."
            )
        summary = summarize_schedule(parsed_courses)

        # Save schedule summary as a user message
        user_message = DBMessage(
            session_id=session_id,
            role="user",
            content=f"Schedule uploaded:\n{summary}"
        )
        db.add(user_message)
        db.commit()
        db.refresh(user_message)

        # Build conversation history for context
        history_messages = db.query(DBMessage).filter(
            DBMessage.session_id == session_id,
            DBMessage.id < user_message.id
        ).order_by(DBMessage.created_at.desc()).limit(6).all()

        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in reversed(history_messages)
        ]

        answer, citations = chatbot_service.recommend_courses_from_schedule(summary, conversation_history)

        # Strip inline bracket citations from schedule-upload responses as well
        try:
            cleaned_answer = re.sub(r"\[[^\]]+?,\s*p\.\s*\d+\]", "", answer)
            cleaned_answer = re.sub(r"\n{2,}", "\n\n", cleaned_answer)
            cleaned_answer = re.sub(r"\s{2,}", " ", cleaned_answer)
            cleaned_answer = cleaned_answer.strip()
        except Exception:
            cleaned_answer = answer

        assistant_message = DBMessage(
            session_id=session_id,
            role='assistant',
            content=cleaned_answer,
            citations=json.dumps(citations)
        )
        db.add(assistant_message)
        db.commit()
        db.refresh(assistant_message)

        citation_objects = [Citation(**c) for c in citations]

        return ScheduleUploadResponse(
            message_id=assistant_message.id,
            answer=answer,
            citations=citation_objects,
            session_id=session_id,
            schedule_summary=summary,
            parsed_courses=[ParsedCourse(**course) for course in parsed_courses],
            schedule_message_id=user_message.id
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing schedule: {str(e)}")


@app.post("/feedback", response_model=FeedbackResponse)
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


@app.get("/messages", response_model=MessagesResponse)
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


@app.get("/sessions", response_model=SessionsResponse)
async def get_user_sessions(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve all sessions for the authenticated user
    
    - Returns list of sessions with metadata
    - Used to display session history/switcher
    """
    try:
        # Get user ID from token
        clerk_user_id = get_user_id_from_token(current_user)
        
        # Get user from database
        user = db.query(DBUser).filter(DBUser.clerk_user_id == clerk_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get all sessions for the user
        sessions = db.query(DBSession).filter(
            DBSession.user_id == user.id
        ).order_by(DBSession.updated_at.desc()).all()
        
        session_infos = [
            SessionInfo(
                session_id=s.session_id,
                created_at=s.created_at,
                updated_at=s.updated_at
            )
            for s in sessions
        ]
        
        return SessionsResponse(sessions=session_infos)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving sessions: {str(e)}")


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
