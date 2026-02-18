from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json

from database import get_db, Session as DBSession, User as DBUser, Message as DBMessage, SessionLocal
from models import ChatRequest, ChatResponse, Citation, FollowUpsResponse
from auth import get_current_user
from chatbot_service import get_chatbot_service
from utils import get_user_from_token, get_session_for_user, clean_answer, get_utc_now, get_conversation_history
from logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


def generate_followups_background(message_id: int, question: str, answer: str, conversation_history: list):
    """
    Background task to generate follow-up suggestions after the main response is sent.
    Updates the message record with follow-ups once generated.
    """
    db = SessionLocal()
    try:
        chatbot = get_chatbot_service()
        followups = chatbot._generate_followups(question, answer, conversation_history)

        message = db.query(DBMessage).filter(DBMessage.id == message_id).first()
        if message:
            message.follow_ups = json.dumps(followups)
            db.commit()
            logger.info(f"Follow-ups generated for message {message_id}: {len(followups)} suggestions")
    except Exception as e:
        logger.error(f"Background follow-up generation failed: {e}")
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
        user = get_user_from_token(db, current_user)
        session = get_session_for_user(db, request.session_id, user, create_if_missing=True)

        # Update session timestamp
        session.updated_at = get_utc_now()
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
        conversation_history = get_conversation_history(db, request.session_id, user_message.id)

        # Get answer from chatbot service
        chatbot = get_chatbot_service()
        answer, citations, question_category, followups = chatbot.get_answer(request.message, conversation_history)

        cleaned_answer = clean_answer(answer)

        assistant_message = DBMessage(
            session_id=request.session_id,
            role='assistant',
            content=cleaned_answer,
            citations=json.dumps(citations)
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
            question_category=question_category,
            follow_ups=followups
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error in /chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Stream a chat response token by token using Server-Sent Events (SSE)."""
    user = get_user_from_token(db, current_user)
    session = get_session_for_user(db, request.session_id, user, create_if_missing=True)

    session.updated_at = get_utc_now()
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
    conversation_history = get_conversation_history(db, request.session_id, user_message.id)

    session_id = request.session_id
    question = request.message

    async def generate():
        chatbot = get_chatbot_service()
        full_answer = ""
        citations = []
        category = ""
        message_id = None

        try:
            async for chunk in chatbot.stream_answer(question, conversation_history):
                if chunk["type"] == "metadata":
                    citations = chunk.get("citations", [])
                    category = chunk.get("category", "")
                    yield f"data: {json.dumps(chunk)}\n\n"

                elif chunk["type"] == "token":
                    yield f"data: {json.dumps(chunk)}\n\n"

                elif chunk["type"] == "done":
                    full_answer = chunk.get("full_answer", "")
                    cleaned_answer = clean_answer(full_answer)

                    # Store assistant message
                    db_local = SessionLocal()
                    try:
                        assistant_message = DBMessage(
                            session_id=session_id,
                            role='assistant',
                            content=cleaned_answer,
                            citations=json.dumps(citations)
                        )
                        db_local.add(assistant_message)
                        db_local.commit()
                        db_local.refresh(assistant_message)
                        message_id = assistant_message.id

                        # Generate follow-ups in background (fire-and-forget)
                        import threading
                        thread = threading.Thread(
                            target=generate_followups_background,
                            args=(message_id, question, cleaned_answer, conversation_history)
                        )
                        thread.start()

                    finally:
                        db_local.close()

                    # Send done event with message_id
                    done_event = {
                        "type": "done",
                        "message_id": message_id,
                        "full_answer": cleaned_answer
                    }
                    yield f"data: {json.dumps(done_event)}\n\n"

        except Exception as e:
            print(f"[ERROR] Streaming error: {e}")
            import traceback
            traceback.print_exc()
            error_event = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/{message_id}/followups", response_model=FollowUpsResponse)
async def get_followups(
    message_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get follow-up suggestions for a specific message.
    Returns empty list with ready=False if follow-ups are still being generated.
    """
    user = get_user_from_token(db, current_user)

    # Get message
    message = db.query(DBMessage).filter(DBMessage.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    # Verify user owns the session
    session = get_session_for_user(db, message.session_id, user)

    # Parse follow-ups
    follow_ups = []
    ready = False

    if message.follow_ups:
        try:
            follow_ups = json.loads(message.follow_ups)
            ready = True
        except json.JSONDecodeError:
            pass

    return FollowUpsResponse(
        message_id=message_id,
        follow_ups=follow_ups,
        ready=ready
    )
