"""
Pydantic models for API requests and responses.

This module defines the data validation and serialization schemas used by the API endpoints,
including models for users, chat sessions, messages, feedback, and more.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# User Models
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


# Request Models
class ChatRequest(BaseModel):
    """Request model for /chat endpoint"""
    session_id: str = Field(..., description="Unique session identifier (UUID)")
    message: str = Field(..., description="User's question")


class FeedbackRequest(BaseModel):
    """Request model for /feedback endpoint"""
    session_id: str = Field(..., description="Session identifier")
    message_id: int = Field(..., description="ID of the assistant message being rated")
    rating: int = Field(..., description="1 for thumbs up, -1 for thumbs down")
    note: Optional[str] = Field(None, description="Optional feedback note")


class EditMessageRequest(BaseModel):
    """Request model for editing a user message"""
    session_id: str = Field(..., description="Session identifier")
    message_id: int = Field(..., description="ID of the user message to edit")
    content: str = Field(..., description="Updated message content")


class EditMessageResponse(BaseModel):
    """Response model for editing a message"""
    success: bool = Field(..., description="Whether the edit succeeded")
    deleted_message_ids: List[int] = Field(default_factory=list, description="Messages removed after edit")


class RegenerateRequest(BaseModel):
    """Request model for regenerating an assistant response"""
    session_id: str = Field(..., description="Session identifier")
    user_message_id: int = Field(..., description="ID of the user message to regenerate from")


# Response Models
class Citation(BaseModel):
    """Citation information for a source"""
    content: str = Field(..., description="The text content of the citation")
    source: str = Field(..., description="Source document name")
    page: Optional[int] = Field(None, description="Page number if available")
    url: Optional[str] = Field(None, description="URL to the source document page")
    doc_type: Optional[str] = Field(None, description="Document type: 'catalog' or 'policy'")


class ChatResponse(BaseModel):
    """Response model for /chat endpoint"""
    message_id: int = Field(..., description="ID of the assistant's message")
    user_message_id: Optional[int] = Field(None, description="ID of the user's message")
    answer: str = Field(..., description="The assistant's answer")
    citations: List[Citation] = Field(default_factory=list, description="List of citations")
    session_id: str = Field(..., description="Session identifier")
    question_category: Optional[str] = Field(None, description="Question classification: 'course_catalog', 'academic_policy', or 'off_topic'")
    follow_ups: List[str] = Field(default_factory=list, description="Suggested follow-up questions tailored to the user")


class ParsedCourse(BaseModel):
    """Parsed course entry extracted from a schedule image/text"""
    course_code: str
    term: Optional[str] = None
    notes: Optional[str] = None


class ScheduleUploadResponse(ChatResponse):
    """Response model for schedule uploads"""
    schedule_summary: str = Field(..., description="Human-readable summary of detected courses")
    parsed_courses: List[ParsedCourse] = Field(default_factory=list, description="Structured parsed courses")
    schedule_message_id: int = Field(..., description="Message ID of the stored schedule summary")


class FeedbackResponse(BaseModel):
    """Response model for /feedback endpoint"""
    success: bool = Field(..., description="Whether feedback was recorded successfully")
    feedback_id: int = Field(..., description="ID of the feedback record")


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


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str = Field(..., description="API status")
    version: str = Field(..., description="API version")
