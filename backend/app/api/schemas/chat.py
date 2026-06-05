from pydantic import BaseModel, Field
from typing import Optional, List


class ChatRequest(BaseModel):
    """Request model for /chat endpoint"""
    session_id: str = Field(..., description="Unique session identifier (UUID)")
    message: str = Field(..., description="User's question")


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


class RegenerateRequest(BaseModel):
    """Request model for regenerating an assistant response"""
    session_id: str = Field(..., description="Session identifier")
    user_message_id: int = Field(..., description="ID of the user message to regenerate from")
