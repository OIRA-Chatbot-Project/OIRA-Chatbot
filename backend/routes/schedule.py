from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
import json

from database import get_db, Session as DBSession, User as DBUser, Message as DBMessage
from models import ScheduleUploadResponse, Citation, ParsedCourse
from auth import get_current_user
from chatbot_service import get_chatbot_service
from schedule_parser import extract_text_from_upload, parse_schedule_entries, summarize_schedule
from utils import get_user_from_token, get_session_for_user, clean_answer, get_utc_now, get_conversation_history

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.post("/upload", response_model=ScheduleUploadResponse)
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
        user = get_user_from_token(db, current_user)

        session = db.query(DBSession).filter(DBSession.session_id == session_id).first()
        if not session:
            session = DBSession(session_id=session_id, user_id=user.id)
            db.add(session)
            db.commit()
        else:
            # Verify session belongs to user
            if session.user_id != user.id:
                raise HTTPException(status_code=403, detail="Session does not belong to user")
            session.updated_at = get_utc_now()
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
        conversation_history = get_conversation_history(db, session_id, user_message.id)

        chatbot = get_chatbot_service()
        answer, citations, question_category, followups = chatbot.recommend_courses_from_schedule(summary, conversation_history)

        cleaned_answer = clean_answer(answer)

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
