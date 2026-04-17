from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass(slots=True)
class AdvisingQuestion:
    """Normalized advising request passed from API to services."""
    user_id: str
    session_id: str
    question: str
    catalog_version_id: str | None = None
    max_recommendations: int = 5

@dataclass(slots=True)
class RetrievalCandidate:
    """One retrieved evidence candidate from catalog search."""
    source_id: str
    course_code: str
    title: str
    matched_text: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class GroundingContext:
    """Evidence package used to constrain LLM responses."""
    question: str
    intent: str
    candidates: list[RetrievalCandidate] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class EligibilityResult:
    """Eligibility evaluation for one recommended course."""
    course_code: str
    is_eligible: bool
    missing_requirements: list[str] = field(default_factory=list)

@dataclass(slots=True)
class CourseRecommendation:
    """Structured course recommendation output."""
    course_code: str
    title: str
    rationale: str
    eligibility: EligibilityResult | None = None

@dataclass(slots=True)
class Citation:
    """Citation metadata that ties answer content to evidence."""
    source_id: str
    source_title: str
    snippet: str
    source_type: str = "course_catalog"

@dataclass(slots=True)
class AdvisingAnswer:
    """Service-layer advising response."""

    session_id: str
    answer_text: str
    citations: list[Citation] = field(default_factory=list)
    recommendations: list[CourseRecommendation] = field(default_factory=list)
    needs_human_advisor: bool = False