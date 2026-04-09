from pydantic import BaseModel, Field
from typing import Optional, List

from app.api.schemas.chat import ChatResponse


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
