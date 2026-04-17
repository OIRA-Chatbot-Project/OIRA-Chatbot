from __future__ import annotations
from fastapi import APIRouter, Depends
from src.api_endpoints.dependencies import get_chat_history_service, get_user_service
from src.api_endpoints.schemas import (
    AcademicRecordRequest,
    ChatMessageResponse,
    FeedbackRequest,
    UserProfileResponse,
    UserProfileUpdateRequest,
    UserRegistrationRequest,
)
from src.services.chat_service import ChatHistoryService
from src.services.user_service import UserService

router = APIRouter(prefix="/api/user", tags=["user"])

@router.post("/register", response_model=UserProfileResponse)
def register_user(
    request: UserRegistrationRequest,
    user_service: UserService = Depends(get_user_service),
) -> UserProfileResponse:
    """Register a new user profile."""
    _ = request
    _ = user_service
    raise NotImplementedError("TODO: implement register_user")

@router.get("/{user_id}", response_model=UserProfileResponse)
def get_user_profile(
    user_id: str,
    user_service: UserService = Depends(get_user_service),
) -> UserProfileResponse:
    """Retrieve one user profile by identifier."""
    _ = user_id
    _ = user_service
    raise NotImplementedError("TODO: implement get_user_profile")

@router.put("/{user_id}", response_model=UserProfileResponse)
def update_user_profile(
    user_id: str,
    request: UserProfileUpdateRequest,
    user_service: UserService = Depends(get_user_service),
) -> UserProfileResponse:
    """Update user profile fields."""
    _ = user_id
    _ = request
    _ = user_service
    raise NotImplementedError("TODO: implement update_user_profile")

@router.post("/feedback")
def add_feedback(
    request: FeedbackRequest,
    user_service: UserService = Depends(get_user_service),
) -> dict[str, str]:
    """Store user feedback on advising output."""
    _ = request
    _ = user_service
    raise NotImplementedError("TODO: implement add_feedback")

@router.get("/{user_id}/chat_history", response_model=list[ChatMessageResponse])
def get_chat_history(
    user_id: str,
    chat_history_service: ChatHistoryService = Depends(get_chat_history_service),
) -> list[ChatMessageResponse]:
    """Retrieve recent chat history across user sessions."""
    _ = user_id
    _ = chat_history_service
    raise NotImplementedError("TODO: implement get_chat_history")

@router.put("/{user_id}/academic_record")
def upsert_academic_record(
    user_id: str,
    request: AcademicRecordRequest,
    user_service: UserService = Depends(get_user_service),
) -> dict[str, str]:
    """Create or update a student's academic record."""
    _ = user_id
    _ = request
    _ = user_service
    raise NotImplementedError("TODO: implement upsert_academic_record")