"""
Schedule processing routes.

This module provides API endpoints for uploading and processing student schedules,
extracting course information, and generating recommendations.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
import re
import json
from datetime import datetime

from database import get_db, Session as DBSession, User as DBUser, Message as DBMessage
from models import ScheduleUploadResponse, Citation, ParsedCourse
from auth import get_current_user, get_user_id_from_token
from chatbot_service import get_chatbot_service
from schedule_parser import extract_text_from_upload, parse_schedule_entries, summarize_schedule

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.post("/upload", response_model=ScheduleUploadResponse)
async def upload_schedule(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Process a student's schedule upload and provide course recommendations.

    Accepts a screenshot or text export of a student's past schedule, extracts the courses,
    and provides tailored recommendations based on the Bucknell course catalog.

    Args:
        session_id: The ID of the session.
        file: The uploaded file (image or text).
        current_user: The authenticated user information.
        db: The database session.

    Returns:
        ScheduleUploadResponse: The extracted schedule summary, parsed courses, and AI recommendations.

    Raises:
        HTTPException: If the user/session is invalid, the file is empty, or parsing fails.
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

        chatbot = get_chatbot_service()
        answer, citations, question_category, followups = chatbot.recommend_courses_from_schedule(summary, conversation_history)

        # Strip inline bracket citations from schedule-upload responses as well
        try:
            cleaned_answer = re.sub(r"\[[^\]]+?,\s*p\.\s*\d+\]", "", answer)
            cleaned_answer = re.sub(r"\n{3,}", "\n\n", cleaned_answer)
            cleaned_answer = re.sub(r"[ \t]{2,}", " ", cleaned_answer)
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
            schedule_message_id=user_message.id,
            question_category=question_category,
            follow_ups=followups
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing schedule: {str(e)}")
