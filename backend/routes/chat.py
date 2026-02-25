from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
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

        # Get answer from chatbot service (async version with parallel LLM calls)
        chatbot = get_chatbot_service()
        answer, citations, question_category, followups = await chatbot.get_answer_async(request.message, conversation_history)

        # Remove inline bracket citations like "[filename, p. 123]" from the answer
        try:
            # 1. Remove citations first (may leave trailing spaces before punctuation)
            cleaned_answer = re.sub(r"\[[^\]]+?,\s*p\.\s*\d+\]", "", answer)
            # 2. Normalize spacing artifacts AFTER citation removal (e.g., "59 ." -> "59.")
            cleaned_answer = re.sub(r"\s+([,.;:!?])", r"\1", cleaned_answer)
            # 3. Collapse excessive blank lines but preserve markdown line breaks
            cleaned_answer = re.sub(r"\n{3,}", "\n\n", cleaned_answer)
            # 4. Collapse repeated spaces/tabs within lines only (preserve leading indentation)
            cleaned_answer = re.sub(r"(?<=\S)[ \t]{2,}", " ", cleaned_answer)
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


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    SSE streaming endpoint for chat responses.

    Events:
    - metadata: {category, citations} — sent before streaming starts
    - token: {token} — raw answer tokens
    - followups: {follow_ups} — generated after stream completes
    - saved: {message_id} — after DB persistence
    - done: {} — signals end of stream
    """
    # Auth + session setup (same as /chat)
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

    # Log user's message
    user_message = DBMessage(
        session_id=request.session_id,
        role="user",
        content=request.message
    )
    db.add(user_message)
    db.commit()

    # Get conversation history
    history_messages = db.query(DBMessage).filter(
        DBMessage.session_id == request.session_id,
        DBMessage.id < user_message.id
    ).order_by(DBMessage.created_at.desc()).limit(6).all()

    conversation_history = [
        {"role": msg.role, "content": msg.content}
        for msg in reversed(history_messages)
    ]

    chatbot = get_chatbot_service()

    async def event_generator():
        final_answer = ""
        final_citations = []
        final_category = "course_catalog"

        try:
            async for event in chatbot.get_answer_streaming(request.message, conversation_history):
                # Forward all events from the service
                yield event

                # Parse the done event to extract final data for DB storage
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

        # Save to DB after stream completes
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
