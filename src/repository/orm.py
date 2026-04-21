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

    course_prefix: str
    course_number: str
    title: str
    description: str
    credits: float | None = None
    requirement_id: str | None = None
    available_terms: list[str] = field(default_factory=list)
    lecture_hours: int | None = None
    lab_hours: int | None = None
    department: str 
    catalog_year: str 


@dataclass(slots=True)
class CourseRequirementRecord:
    """Normalized prerequisite/corequisite expression linked to a course."""

    requirement_id: str
    course_prefix: str
    course_number: str
    requirement_type: str 
    expression_text: str
    parsed_expression: dict[str, Any] = field(default_factory=dict)
    catalog_year: str


@dataclass(slots=True)
class CatalogChunkRecord:
    """Embedding chunk representing one retrievable course catalog segment."""

    chunk_id: str
    catalog_year: str
    source_course_code: str
    source_field: str
    chunk_text: str
    embedding_model: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DocumentRecord:
    """Generic source document metadata for RAG sources."""

    document_id: str
    document_type: str
    file_name: str
    storage_uri: str
    uploaded_by: str
    created_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class UserRecord:
    """Application user profile."""

    user_id: str
    clerk_id: str
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
