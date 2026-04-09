"""Message retrieval and editing routes."""
from fastapi import APIRouter, Depends, Query

from app.api.deps import get_message_service, get_session_repo, get_user_service
from app.api.schemas.message import (
    MessagesResponse,
    EditMessageRequest,
    EditMessageResponse,
)
from app.core.auth import get_current_user, get_user_id_from_token
from app.data.repositories.session_repository import SQLSessionRepository
from app.services.message_service import MessageService
from app.services.user_service import UserService

router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("", response_model=MessagesResponse)
async def get_messages(
    session_id: str = Query(..., description="Session identifier"),
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
    message_service: MessageService = Depends(get_message_service),
    session_repo: SQLSessionRepository = Depends(get_session_repo),
):
    """Get all messages for a session."""
    clerk_user_id = get_user_id_from_token(current_user)
    user = user_service.require_by_clerk_id(clerk_user_id)
    messages = message_service.get_for_session(session_id, user.id, session_repo)
    return MessagesResponse(session_id=session_id, messages=messages)


@router.post("/edit", response_model=EditMessageResponse)
async def edit_message(
    request: EditMessageRequest,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
    message_service: MessageService = Depends(get_message_service),
    session_repo: SQLSessionRepository = Depends(get_session_repo),
):
    """Edit a user message and cascade-delete subsequent messages."""
    clerk_user_id = get_user_id_from_token(current_user)
    user = user_service.require_by_clerk_id(clerk_user_id)
    result = message_service.edit_message(
        message_id=request.message_id,
        session_id=request.session_id,
        user_id=user.id,
        new_content=request.content,
        session_repo=session_repo,
    )
    return EditMessageResponse(
        success=result.success,
        deleted_message_ids=result.deleted_message_ids,
    )
