"""
User management routes.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from infra.db.engine import get_db
from infra.db.models import User as DBUser
from api.schemas import UserCreate, UserResponse
from auth import get_current_user, get_user_id_from_token

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse)
async def create_or_get_user(
    user_data: UserCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new user or retrieve an existing user."""
    try:
        clerk_user_id = get_user_id_from_token(current_user)
        if clerk_user_id != user_data.clerk_user_id:
            raise HTTPException(status_code=403, detail="Cannot create user for different clerk_user_id")

        existing_user = db.query(DBUser).filter(
            DBUser.clerk_user_id == user_data.clerk_user_id
        ).first()

        if existing_user:
            if user_data.email != existing_user.email or user_data.name != existing_user.name:
                existing_user.email = user_data.email
                existing_user.name = user_data.name
                existing_user.updated_at = datetime.now(datetime.UTC) if hasattr(datetime, 'UTC') else datetime.utcnow()
                db.commit()
                db.refresh(existing_user)

            return UserResponse(
                id=existing_user.id,
                clerk_user_id=existing_user.clerk_user_id,
                email=existing_user.email,
                name=existing_user.name,
                created_at=existing_user.created_at
            )

        new_user = DBUser(
            clerk_user_id=user_data.clerk_user_id,
            email=user_data.email,
            name=user_data.name
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return UserResponse(
            id=new_user.id,
            clerk_user_id=new_user.clerk_user_id,
            email=new_user.email,
            name=new_user.name,
            created_at=new_user.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating/retrieving user: {str(e)}")
