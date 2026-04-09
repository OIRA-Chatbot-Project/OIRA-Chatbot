from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.api.schemas.chat import Citation


class MessageResponse(BaseModel):
    """Individual message in chat history"""
    id: int = Field(..., description="Message ID")
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    citations: Optional[List[Citation]] = Field(None, description="Citations (for assistant messages)")
    created_at: datetime = Field(..., description="When the message was created")


class MessagesResponse(BaseModel):
    """Response model for /messages endpoint"""
    session_id: str = Field(..., description="Session identifier")
    messages: List[MessageResponse] = Field(default_factory=list, description="List of messages in the session")


class EditMessageRequest(BaseModel):
    """Request model for editing a user message"""
    session_id: str = Field(..., description="Session identifier")
    message_id: int = Field(..., description="ID of the user message to edit")
    content: str = Field(..., description="Updated message content")


class EditMessageResponse(BaseModel):
    """Response model for editing a message"""
    success: bool = Field(..., description="Whether the edit succeeded")
    deleted_message_ids: List[int] = Field(default_factory=list, description="Messages removed after edit")
