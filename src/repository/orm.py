from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

def utc_now() -> datetime:
    """Return timezone-aware UTC timestamp for record defaults."""
    return datetime.now(timezone.utc)

@dataclass(slots=True)
class CourseRecord:
    """Structured course catalog entity."""
    course_id: str
    course_code: str
    title: str
    description: str
    prerequisites: str | None = None
    corequisites: str | None = None
    credits: float | None = None
    department: str | None = None
    catalog_version_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class CourseRequirementRecord:
    """Normalized prerequisite/corequisite expression linked to a course."""
    requirement_id: str
    course_code: str
    requirement_type: str
    expression_text: str
    parsed_expression: dict[str, Any] = field(default_factory=dict)
    catalog_version_id: str | None = None

@dataclass(slots=True)
class CatalogChunkRecord:
    """Embedding chunk representing one retrievable course catalog segment."""
    chunk_id: str
    catalog_version_id: str
    source_course_code: str
    source_field: str
    chunk_text: str
    embedding_model: str
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class CatalogDocumentRecord:
    """Catalog source document metadata."""
    document_id: str
    catalog_version_id: str
    file_name: str
    content_type: str
    storage_uri: str
    uploaded_by: str
    created_at: datetime = field(default_factory=utc_now)

@dataclass(slots=True)
class UserRecord:
    """Application user profile."""
    user_id: str
    email: str
    first_name: str
    last_name: str
    created_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AcademicRecord:
    """Student course completion and enrollment context."""
    user_id: str
    completed_courses: list[str] = field(default_factory=list)
    current_courses: list[str] = field(default_factory=list)
    target_term: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class ChatSessionRecord:
    """Chat session metadata for advising conversations."""
    session_id: str
    user_id: str
    title: str
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

@dataclass(slots=True)
class ChatMessageRecord:
    """One message within a chat session."""
    message_id: str
    session_id: str
    role: str
    content: str
    created_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class FeedbackRecord:
    """User feedback on answer quality."""
    feedback_id: str
    user_id: str
    session_id: str
    message_id: str
    rating: int
    comment: str | None = None
    created_at: datetime = field(default_factory=utc_now)