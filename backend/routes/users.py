from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db, User as DBUser
from models import UserCreate, UserResponse
from auth import get_current_user, get_user_id_from_token
from utils import get_utc_now

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse)
async def create_or_get_user(
    user_data: UserCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new user or retrieve existing user
    
    - Checks if user already exists by clerk_user_id
    - Creates new user if doesn't exist
    - Returns user information
    """
    try:
        # Verify the user making request matches the user being created
        clerk_user_id = get_user_id_from_token(current_user)
        if clerk_user_id != user_data.clerk_user_id:
            raise HTTPException(status_code=403, detail="Cannot create user for different clerk_user_id")
        
        # Check if user already exists
        existing_user = db.query(DBUser).filter(
            DBUser.clerk_user_id == user_data.clerk_user_id
        ).first()
        
        if existing_user:
            # Update user info if changed
            if user_data.email != existing_user.email or user_data.name != existing_user.name:
                existing_user.email = user_data.email
                existing_user.name = user_data.name
                existing_user.updated_at = get_utc_now()
                db.commit()
                db.refresh(existing_user)
            
            return UserResponse(
                id=existing_user.id,
                clerk_user_id=existing_user.clerk_user_id,
                email=existing_user.email,
                name=existing_user.name,
                created_at=existing_user.created_at
            )
        
        # Create new user
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
