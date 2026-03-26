"""
Chat interaction routes.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import asyncio
import re
import json
from datetime import datetime

from infra.db.engine import get_db, SessionLocal
from infra.db.models import Session as DBSession, User as DBUser, Message as DBMessage, Feedback as DBFeedback
from api.schemas import ChatRequest, ChatResponse, Citation, RegenerateRequest
from auth import get_current_user, get_user_id_from_token
from core.container import get_chatbot_service
from core.settings import settings

router = APIRouter(prefix="/chat", tags=["chat"])


async def _run_post_response_tasks(
    session_id: str,
    user_message_content: str,
    clerk_user_id: str,
) -> None:
    """Run background memory tasks after the response has been sent."""
    if not settings.rag.ENABLE_CONVERSATION_MEMORY:
        return

    db = SessionLocal()
    try:
        chatbot = get_chatbot_service()

        user = db.query(DBUser).filter(DBUser.clerk_user_id == clerk_user_id).first()
        if user:
            existing_facts: dict = {}
            if user.profile_facts:
                try:
                    existing_facts = json.loads(user.profile_facts)
                except json.JSONDecodeError:
                    existing_facts = {}

            updated_facts = await chatbot._extract_user_facts(user_message_content, existing_facts)
            if updated_facts != existing_facts:
                user.profile_facts = json.dumps(updated_facts)
                db.commit()

        total_count = db.query(DBMessage).filter(
            DBMessage.session_id == session_id
        ).count()

        if total_count > settings.rag.SUMMARY_WINDOW_SIZE:
            session_obj = db.query(DBSession).filter(
                DBSession.session_id == session_id
            ).first()
            if session_obj:
                messages_to_keep = (
                    db.query(DBMessage)
                    .filter(DBMessage.session_id == session_id)
                    .order_by(DBMessage.created_at.desc())
                    .limit(settings.rag.SUMMARY_WINDOW_SIZE)
                    .all()
                )
                keep_ids = {m.id for m in messages_to_keep}
                older_messages = (
                    db.query(DBMessage)
                    .filter(
                        DBMessage.session_id == session_id,
                        ~DBMessage.id.in_(keep_ids),
                    )
                    .order_by(DBMessage.created_at.asc())
                    .all()
                )
                messages_to_summarize = [
                    {"role": m.role, "content": m.content} for m in older_messages
                ]
                existing_summary = session_obj.conversation_summary or None
                new_summary = await chatbot._summarize_conversation(
                    session_id, existing_summary, messages_to_summarize
                )
                if new_summary and new_summary != existing_summary:
                    session_obj.conversation_summary = new_summary
                    db.commit()

    except Exception as e:
        print(f"[WARNING] Background memory task failed for session {session_id}: {e}")
    finally:
        db.close()


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Process a chat message and return an answer with citations."""
    try:
        clerk_user_id = get_user_id_from_token(current_user)

        user = db.query(DBUser).filter(DBUser.clerk_user_id == clerk_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found. Please sign up first.")

        session = db.query(DBSession).filter(DBSession.session_id == request.session_id).first()
        if not session:
            session = DBSession(session_id=request.session_id, user_id=user.id)
            db.add(session)
            db.commit()
        else:
            if session.user_id != user.id:
                raise HTTPException(status_code=403, detail="Session does not belong to user")
            session.updated_at = datetime.now(datetime.UTC) if hasattr(datetime, 'UTC') else datetime.utcnow()
            db.commit()

        user_message = DBMessage(
            session_id=request.session_id,
            role="user",
            content=request.message
        )
        db.add(user_message)
        db.commit()

        history_messages = db.query(DBMessage).filter(
            DBMessage.session_id == request.session_id,
            DBMessage.id < user_message.id
        ).order_by(DBMessage.created_at.desc()).limit(6).all()

        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in reversed(history_messages)
        ]

        session_summary = (session.conversation_summary or None) if session else None

        user_profile: dict = {}
        if user.profile_facts:
            try:
                user_profile = json.loads(user.profile_facts)
            except json.JSONDecodeError:
                user_profile = {}

        chatbot = get_chatbot_service()
        answer, citations, question_category, followups = await chatbot.get_answer_async(
            request.message,
            conversation_history,
            conversation_summary=session_summary,
            user_profile=user_profile or None,
        )

        try:
            cleaned_answer = re.sub(r"\[[^\]]+?,\s*p\.\s*\d+\]", "", answer)
            cleaned_answer = re.sub(r"\s+([,.;:!?])", r"\1", cleaned_answer)
            cleaned_answer = re.sub(r"\n{3,}", "\n\n", cleaned_answer)
            cleaned_answer = re.sub(r"(?<=\S)[ \t]{2,}", " ", cleaned_answer)
            cleaned_answer = cleaned_answer.strip()
        except Exception:
            cleaned_answer = answer

        assistant_message = DBMessage(
            session_id=request.session_id,
            role='assistant',
            content=cleaned_answer,
            citations=json.dumps(citations)
        )
        db.add(assistant_message)
        db.commit()
        db.refresh(assistant_message)

        citation_objects = [Citation(**c) for c in citations]

        asyncio.create_task(
            _run_post_response_tasks(
                session_id=request.session_id,
                user_message_content=request.message,
                clerk_user_id=clerk_user_id,
            )
        )

        return ChatResponse(
            message_id=assistant_message.id,
            user_message_id=user_message.id,
            answer=cleaned_answer,
            citations=citation_objects,
            session_id=request.session_id,
            question_category=question_category,
            follow_ups=followups
        )

    except Exception as e:
        db.rollback()
        print(f"ERROR in /chat endpoint: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")


def _clean_answer(answer: str) -> str:
    """Remove inline bracket citations and normalize spacing."""
    try:
        cleaned = re.sub(r"\[[^\]]+?,\s*p\.\s*\d+\]", "", answer)
        cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = re.sub(r"(?<=\S)[ \t]{2,}", " ", cleaned)
        return cleaned.strip()
    except Exception:
        return answer


@router.post("/regenerate", response_model=ChatResponse)
async def regenerate(
    request: RegenerateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Regenerate an assistant answer for an existing user message."""
    try:
        clerk_user_id = get_user_id_from_token(current_user)

        user = db.query(DBUser).filter(DBUser.clerk_user_id == clerk_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found. Please sign up first.")

        session = db.query(DBSession).filter(
            DBSession.session_id == request.session_id,
            DBSession.user_id == user.id
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        user_message = db.query(DBMessage).filter(
            DBMessage.id == request.user_message_id,
            DBMessage.session_id == request.session_id
        ).first()
        if not user_message:
            raise HTTPException(status_code=404, detail="Message not found")
        if user_message.role != "user":
            raise HTTPException(status_code=400, detail="Can only regenerate from a user message")

        delete_ids = [
            mid for (mid,) in db.query(DBMessage.id).filter(
                DBMessage.session_id == request.session_id,
                DBMessage.id > request.user_message_id
            ).all()
        ]
        if delete_ids:
            db.query(DBFeedback).filter(DBFeedback.message_id.in_(delete_ids)).delete(synchronize_session=False)
            db.query(DBMessage).filter(DBMessage.id.in_(delete_ids)).delete(synchronize_session=False)

        session.updated_at = datetime.now(datetime.UTC) if hasattr(datetime, 'UTC') else datetime.utcnow()

        history_messages = db.query(DBMessage).filter(
            DBMessage.session_id == request.session_id,
            DBMessage.id < user_message.id
        ).order_by(DBMessage.created_at.desc()).limit(6).all()

        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in reversed(history_messages)
        ]

        session_summary = (session.conversation_summary or None) if session else None

        user_profile: dict = {}
        if user.profile_facts:
            try:
                user_profile = json.loads(user.profile_facts)
            except json.JSONDecodeError:
                user_profile = {}

        chatbot = get_chatbot_service()
        answer, citations, question_category, followups = await chatbot.get_answer_async(
            user_message.content,
            conversation_history,
            conversation_summary=session_summary,
            user_profile=user_profile or None,
        )

        cleaned_answer = _clean_answer(answer)

        assistant_message = DBMessage(
            session_id=request.session_id,
            role='assistant',
            content=cleaned_answer,
            citations=json.dumps(citations)
        )
        db.add(assistant_message)
        db.commit()
        db.refresh(assistant_message)

        citation_objects = [Citation(**c) for c in citations]

        asyncio.create_task(
            _run_post_response_tasks(
                session_id=request.session_id,
                user_message_content=user_message.content,
                clerk_user_id=clerk_user_id,
            )
        )

        return ChatResponse(
            message_id=assistant_message.id,
            answer=cleaned_answer,
            citations=citation_objects,
            session_id=request.session_id,
            question_category=question_category,
            follow_ups=followups
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"ERROR in /chat/regenerate endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing regenerate: {str(e)}")


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """SSE streaming endpoint for chat responses."""
    clerk_user_id = get_user_id_from_token(current_user)
    user = db.query(DBUser).filter(DBUser.clerk_user_id == clerk_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Please sign up first.")

    session = db.query(DBSession).filter(DBSession.session_id == request.session_id).first()
    if not session:
        session = DBSession(session_id=request.session_id, user_id=user.id)
        db.add(session)
        db.commit()
    else:
        if session.user_id != user.id:
            raise HTTPException(status_code=403, detail="Session does not belong to user")
        session.updated_at = datetime.now(datetime.UTC) if hasattr(datetime, 'UTC') else datetime.utcnow()
        db.commit()

    user_message = DBMessage(
        session_id=request.session_id,
        role="user",
        content=request.message
    )
    db.add(user_message)
    db.commit()

    history_messages = db.query(DBMessage).filter(
        DBMessage.session_id == request.session_id,
        DBMessage.id < user_message.id
    ).order_by(DBMessage.created_at.desc()).limit(6).all()

    conversation_history = [
        {"role": msg.role, "content": msg.content}
        for msg in reversed(history_messages)
    ]

    session_summary_stream = (session.conversation_summary or None) if session else None

    user_profile_stream: dict = {}
    if user.profile_facts:
        try:
            user_profile_stream = json.loads(user.profile_facts)
        except json.JSONDecodeError:
            user_profile_stream = {}

    chatbot = get_chatbot_service()
    user_message_id = user_message.id
    _clerk_user_id_stream = clerk_user_id

    async def event_generator():
        final_answer = ""
        final_citations = []
        final_category = "course_catalog"

        try:
            user_payload = json.dumps({"message_id": user_message_id})
            yield f"event: user\ndata: {user_payload}\n\n"
            async for event in chatbot.get_answer_streaming(
                request.message,
                conversation_history,
                conversation_summary=session_summary_stream,
                user_profile=user_profile_stream or None,
            ):
                yield event

                if event.startswith("event: done"):
                    data_line = event.split("data: ", 1)[1].split("\n")[0]
                    done_data = json.loads(data_line)
                    final_answer = done_data.get("answer", "")
                    final_citations = done_data.get("citations", [])
                    final_category = done_data.get("category", "course_catalog")

        except Exception as e:
            print(f"[ERROR] Streaming error: {e}")
            error_payload = json.dumps({"error": str(e)})
            yield f"event: error\ndata: {error_payload}\n\n"
            return

        try:
            cleaned_answer = _clean_answer(final_answer)
            assistant_message = DBMessage(
                session_id=request.session_id,
                role="assistant",
                content=cleaned_answer,
                citations=json.dumps(final_citations)
            )
            db.add(assistant_message)
            db.commit()
            db.refresh(assistant_message)

            saved_payload = json.dumps({"message_id": assistant_message.id})
            yield f"event: saved\ndata: {saved_payload}\n\n"

            asyncio.create_task(
                _run_post_response_tasks(
                    session_id=request.session_id,
                    user_message_content=request.message,
                    clerk_user_id=_clerk_user_id_stream,
                )
            )
        except Exception as e:
            print(f"[ERROR] DB save error after stream: {e}")
            db.rollback()
            error_payload = json.dumps({"error": "Failed to save message"})
            yield f"event: error\ndata: {error_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/regenerate/stream")
async def regenerate_stream(
    request: RegenerateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """SSE streaming endpoint for regenerating an assistant response."""
    clerk_user_id = get_user_id_from_token(current_user)
    user = db.query(DBUser).filter(DBUser.clerk_user_id == clerk_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Please sign up first.")

    session = db.query(DBSession).filter(
        DBSession.session_id == request.session_id,
        DBSession.user_id == user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    user_message = db.query(DBMessage).filter(
        DBMessage.id == request.user_message_id,
        DBMessage.session_id == request.session_id
    ).first()
    if not user_message:
        raise HTTPException(status_code=404, detail="Message not found")
    if user_message.role != "user":
        raise HTTPException(status_code=400, detail="Can only regenerate from a user message")

    delete_ids = [
        mid for (mid,) in db.query(DBMessage.id).filter(
            DBMessage.session_id == request.session_id,
            DBMessage.id > request.user_message_id
        ).all()
    ]
    if delete_ids:
        db.query(DBFeedback).filter(DBFeedback.message_id.in_(delete_ids)).delete(synchronize_session=False)
        db.query(DBMessage).filter(DBMessage.id.in_(delete_ids)).delete(synchronize_session=False)

    session.updated_at = datetime.now(datetime.UTC) if hasattr(datetime, 'UTC') else datetime.utcnow()
    db.commit()

    history_messages = db.query(DBMessage).filter(
        DBMessage.session_id == request.session_id,
        DBMessage.id < user_message.id
    ).order_by(DBMessage.created_at.desc()).limit(6).all()

    conversation_history = [
        {"role": msg.role, "content": msg.content}
        for msg in reversed(history_messages)
    ]

    regen_session_summary = (session.conversation_summary or None) if session else None

    regen_user_profile: dict = {}
    if user.profile_facts:
        try:
            regen_user_profile = json.loads(user.profile_facts)
        except json.JSONDecodeError:
            regen_user_profile = {}

    _regen_clerk_user_id = clerk_user_id
    chatbot = get_chatbot_service()

    async def event_generator():
        final_answer = ""
        final_citations = []

        try:
            async for event in chatbot.get_answer_streaming(
                user_message.content,
                conversation_history,
                conversation_summary=regen_session_summary,
                user_profile=regen_user_profile or None,
            ):
                yield event

                if event.startswith("event: done"):
                    data_line = event.split("data: ", 1)[1].split("\n")[0]
                    done_data = json.loads(data_line)
                    final_answer = done_data.get("answer", "")
                    final_citations = done_data.get("citations", [])

        except Exception as e:
            print(f"[ERROR] Regenerate streaming error: {e}")
            error_payload = json.dumps({"error": str(e)})
            yield f"event: error\ndata: {error_payload}\n\n"
            return

        try:
            cleaned_answer = _clean_answer(final_answer)
            assistant_message = DBMessage(
                session_id=request.session_id,
                role="assistant",
                content=cleaned_answer,
                citations=json.dumps(final_citations)
            )
            db.add(assistant_message)
            db.commit()
            db.refresh(assistant_message)

            saved_payload = json.dumps({"message_id": assistant_message.id})
            yield f"event: saved\ndata: {saved_payload}\n\n"

            asyncio.create_task(
                _run_post_response_tasks(
                    session_id=request.session_id,
                    user_message_content=user_message.content,
                    clerk_user_id=_regen_clerk_user_id,
                )
            )
        except Exception as e:
            print(f"[ERROR] DB save error after regenerate stream: {e}")
            db.rollback()
            error_payload = json.dumps({"error": "Failed to save message"})
            yield f"event: error\ndata: {error_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
