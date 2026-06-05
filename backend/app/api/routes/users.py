"""User management routes."""
from fastapi import APIRouter, Depends

from app.api.deps import get_user_service
from app.api.schemas.user import UserCreate, UserResponse
from app.core.auth import get_current_user, get_user_id_from_token
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse)
async def create_user(
    request: UserCreate,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    """Create or update a user record."""
    requesting_clerk_id = get_user_id_from_token(current_user)
    user = user_service.upsert_user(
        clerk_user_id=request.clerk_user_id,
        email=request.email,
        name=request.name,
        requesting_clerk_id=requesting_clerk_id,
    )
    return UserResponse(
        id=user.id,
        clerk_user_id=user.clerk_user_id,
        email=user.email,
        name=user.name,
        created_at=user.created_at,
    )
