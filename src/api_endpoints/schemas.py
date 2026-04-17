from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field

class CitationResponse(BaseModel):
    """API citation payload for answer traceability."""
    source_id: str
    source_title: str
    snippet: str
    source_type: str = "course_catalog"

class CourseRecommendationResponse(BaseModel):
    """API payload for one recommended course."""
    course_code: str
    title: str
    rationale: str
    is_eligible: bool | None = None
    missing_requirements: list[str] = Field(default_factory=list)

class InitializeChatRequest(BaseModel):
    """Request body for creating a new chat session."""
    user_id: str
    title: str = "Advising Session"

class InitializeChatResponse(BaseModel):
    """Response body for new chat session creation."""
    session_id: str

class AdvisingQuestionRequest(BaseModel):
    """Primary advising question request body."""
    user_id: str
    session_id: str
    question: str
    catalog_version_id: str | None = None
    max_recommendations: int = 5

class AdvisingAnswerResponse(BaseModel):
    """Grounded advising answer response body."""
    session_id: str
    answer: str
    citations: list[CitationResponse] = Field(default_factory=list)
    recommendations: list[CourseRecommendationResponse] = Field(default_factory=list)
    needs_human_advisor: bool = False

class CatalogUploadRequest(BaseModel):
    """Catalog upload request body for ingestion."""
    user_id: str
    catalog_version_id: str
    file_name: str
    content_type: str
    raw_text: str

class CatalogUploadResponse(BaseModel):
    """Catalog upload response body."""
    document_id: str
    catalog_version_id: str
    status: str

class CatalogDocumentResponse(BaseModel):
    """Catalog document metadata response."""
    document_id: str
    catalog_version_id: str
    file_name: str
    content_type: str
    storage_uri: str
    uploaded_by: str
    created_at: datetime

class UserRegistrationRequest(BaseModel):
    """Request body for user registration."""
    email: str
    first_name: str
    last_name: str

class UserProfileResponse(BaseModel):
    """Response body for user profile queries."""
    user_id: str
    email: str
    first_name: str
    last_name: str

class UserProfileUpdateRequest(BaseModel):
    """Request body for user profile updates."""
    user_id: str
    email: str
    first_name: str
    last_name: str

class AcademicRecordRequest(BaseModel):
    """Request body for student academic context updates."""
    completed_courses: list[str] = Field(default_factory=list)
    current_courses: list[str] = Field(default_factory=list)
    target_term: str | None = None

class FeedbackRequest(BaseModel):
    """Request body for answer-quality feedback."""
    user_id: str
    session_id: str
    message_id: str
    rating: int = Field(ge=1, le=5)
    comment: str | None = None

class ChatMessageResponse(BaseModel):
    """API payload for one chat history message."""
    message_id: str
    session_id: str
    role: str
    content: str
    created_at: datetime