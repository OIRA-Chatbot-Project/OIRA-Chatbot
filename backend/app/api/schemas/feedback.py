from pydantic import BaseModel, Field
from typing import Optional


class FeedbackRequest(BaseModel):
    """Request model for /feedback endpoint"""
    session_id: str = Field(..., description="Session identifier")
    message_id: int = Field(..., description="ID of the assistant message being rated")
    rating: int = Field(..., description="1 for thumbs up, -1 for thumbs down")
    note: Optional[str] = Field(None, description="Optional feedback note")


class FeedbackResponse(BaseModel):
    """Response model for /feedback endpoint"""
    success: bool = Field(..., description="Whether feedback was recorded successfully")
    feedback_id: int = Field(..., description="ID of the feedback record")
