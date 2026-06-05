from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class SessionInfo(BaseModel):
    """Session information"""
    session_id: str = Field(..., description="Session identifier")
    title: Optional[str] = Field(None, description="AI-generated session title")
    created_at: datetime = Field(..., description="When the session was created")
    updated_at: datetime = Field(..., description="When the session was last updated")
    has_messages: bool = Field(default=False, description="Whether the session has any messages")


class SessionsResponse(BaseModel):
    """Response model for /sessions endpoint"""
    sessions: List[SessionInfo] = Field(default_factory=list, description="List of user sessions")


class GenerateTitleRequest(BaseModel):
    """Request model for generating a session title"""
    session_id: str = Field(..., description="The unique identifier of the session")
    first_message: str = Field(..., description="The first message content to base the title on")


class GenerateTitleResponse(BaseModel):
    """Response model containing the generated session title"""
    title: str = Field(..., description="The generated title for the session")


class UpdateSessionRequest(BaseModel):
    """Request model for updating a session"""
    title: Optional[str] = Field(None, description="The new title for the session")
