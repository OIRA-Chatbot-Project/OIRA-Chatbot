"""Chat interaction routes: send, regenerate, and SSE streaming."""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import get_chat_service
from app.api.schemas.chat import ChatRequest, ChatResponse, Citation, RegenerateRequest
from app.core.auth import get_current_user, get_user_id_from_token
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    """Process a chat message and return an answer with citations."""
    clerk_user_id = get_user_id_from_token(current_user)
    result = await chat_service.handle_chat(request.session_id, request.message, clerk_user_id)
    return ChatResponse(
        message_id=result.message_id,
        user_message_id=result.user_message_id,
        answer=result.answer,
        citations=[Citation(**c) for c in result.citations],
        session_id=result.session_id,
        question_category=result.question_category,
        follow_ups=result.follow_ups,
    )


@router.post("/regenerate", response_model=ChatResponse)
async def regenerate(
    request: RegenerateRequest,
    current_user: dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    """Regenerate an assistant answer for an existing user message."""
    clerk_user_id = get_user_id_from_token(current_user)
    result = await chat_service.handle_regenerate(
        request.session_id, request.user_message_id, clerk_user_id
    )
    return ChatResponse(
        message_id=result.message_id,
        answer=result.answer,
        citations=[Citation(**c) for c in result.citations],
        session_id=result.session_id,
        question_category=result.question_category,
        follow_ups=result.follow_ups,
    )


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    """SSE streaming endpoint for chat responses."""
    clerk_user_id = get_user_id_from_token(current_user)
    context = await chat_service.prepare_stream(request.session_id, request.message, clerk_user_id)
    return StreamingResponse(
        chat_service.stream_events(context),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/regenerate/stream")
async def regenerate_stream(
    request: RegenerateRequest,
    current_user: dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    """SSE streaming endpoint for regenerating an assistant response."""
    clerk_user_id = get_user_id_from_token(current_user)
    context = await chat_service.prepare_regenerate_stream(
        request.session_id, request.user_message_id, clerk_user_id
    )
    return StreamingResponse(
        chat_service.regenerate_stream_events(context),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
