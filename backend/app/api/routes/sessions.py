"""Session management routes."""
from fastapi import APIRouter, Depends

from app.api.deps import get_session_service, get_user_service
from app.api.schemas.session import (
    SessionsResponse,
    GenerateTitleRequest,
    GenerateTitleResponse,
    UpdateSessionRequest,
)
from app.core.auth import get_current_user, get_user_id_from_token
from app.services.session_service import SessionService
from app.services.user_service import UserService

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=SessionsResponse)
async def get_sessions(
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
    session_service: SessionService = Depends(get_session_service),
):
    """Get all sessions for the authenticated user."""
    clerk_user_id = get_user_id_from_token(current_user)
    user = user_service.require_by_clerk_id(clerk_user_id)
    sessions = session_service.get_sessions_for_user(user.id)
    return SessionsResponse(sessions=sessions)


@router.post("/generate-title", response_model=GenerateTitleResponse)
async def generate_title(
    request: GenerateTitleRequest,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
    session_service: SessionService = Depends(get_session_service),
):
    """Generate an AI title for a session."""
    clerk_user_id = get_user_id_from_token(current_user)
    user = user_service.require_by_clerk_id(clerk_user_id)
    title = session_service.generate_title(request.session_id, user.id, request.first_message)
    return GenerateTitleResponse(title=title)


@router.put("/{session_id}", response_model=GenerateTitleResponse)
async def update_session(
    session_id: str,
    request: UpdateSessionRequest,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
    session_service: SessionService = Depends(get_session_service),
):
    """Update a session's title."""
    clerk_user_id = get_user_id_from_token(current_user)
    user = user_service.require_by_clerk_id(clerk_user_id)
    if request.title is not None:
        session_service.update_title(session_id, user.id, request.title)
    session = session_service.require_owned_by(session_id, user.id)
    return GenerateTitleResponse(title=session.title or "")


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
    session_service: SessionService = Depends(get_session_service),
):
    """Delete a session and all its messages."""
    clerk_user_id = get_user_id_from_token(current_user)
    user = user_service.require_by_clerk_id(clerk_user_id)
    session_service.delete(session_id, user.id)
    return {"success": True}
