from __future__ import annotations
from src.repository.course_repository import CourseRepository
from src.repository.knowledge_repository import CatalogVectorRepository
from src.repository.orm import CourseRecord
from src.services.contracts import Citation, GroundingContext, RetrievalCandidate

class IntentClassificationService:
    """Classifies advising question intent for routing and prompt shaping."""
    def classify_question_intent(self, question: str) -> str:
        raise NotImplementedError(
            "TODO: implement IntentClassificationService.classify_question_intent"
        )

class CatalogRetrievalService:
    """Combines structured and vector retrieval for catalog grounding."""
    def __init__(
        self,
        course_repository: CourseRepository,
        vector_repository: CatalogVectorRepository,
    ) -> None:
        self.course_repository = course_repository
        self.vector_repository = vector_repository

    def retrieve_relevant_courses(
        self,
        question: str,
        catalog_version_id: str | None = None,
        limit: int = 8,
    ) -> list[RetrievalCandidate]:
        raise NotImplementedError(
            "TODO: implement CatalogRetrievalService.retrieve_relevant_courses"
        )

    def get_course_details(
        self, course_codes: list[str], catalog_version_id: str | None = None
    ) -> list[CourseRecord]:
        raise NotImplementedError(
            "TODO: implement CatalogRetrievalService.get_course_details"
        )

class GroundingService:
    """Builds and validates answer grounding context."""

    def build_grounding_context(
        self, question: str, intent: str, candidates: list[RetrievalCandidate]
    ) -> GroundingContext:
        raise NotImplementedError("TODO: implement GroundingService.build_grounding_context")

    def validate_grounding_coverage(self, context: GroundingContext) -> bool:
        raise NotImplementedError(
            "TODO: implement GroundingService.validate_grounding_coverage"
        )

class AnswerGenerationService:
    """Produces final answer text using grounded context."""

    def generate_grounded_answer(self, context: GroundingContext) -> str:
        raise NotImplementedError(
            "TODO: implement AnswerGenerationService.generate_grounded_answer"
        )

    def generate_insufficient_evidence_response(self, question: str) -> str:
        raise NotImplementedError(
            "TODO: implement AnswerGenerationService.generate_insufficient_evidence_response"
        )

class CitationService:
    """Creates and attaches citations for answer traceability."""
    def build_citations(self, candidates: list[RetrievalCandidate]) -> list[Citation]:
        raise NotImplementedError("TODO: implement CitationService.build_citations")