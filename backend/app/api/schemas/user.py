from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    """Request model for creating/retrieving a user"""
    clerk_user_id: str = Field(..., description="Clerk user ID")
    email: str = Field(..., description="User email")
    name: Optional[str] = Field(None, description="User name")


class UserResponse(BaseModel):
    """Response model for user data"""
    id: int = Field(..., description="Internal user ID")
    clerk_user_id: str = Field(..., description="Clerk user ID")
    email: str = Field(..., description="User email")
    name: Optional[str] = Field(None, description="User name")
    created_at: datetime = Field(..., description="When the user was created")
