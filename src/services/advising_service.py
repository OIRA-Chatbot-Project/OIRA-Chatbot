from __future__ import annotations
from collections.abc import AsyncIterator
from src.repository.course_repository import CourseRequirementRepository
from src.repository.unit_of_work import UnitOfWork
from src.repository.user_repository import AcademicRecordRepository
from src.services.chat_service import ChatHistoryService
from src.services.contracts import (
    AdvisingAnswer,
    AdvisingQuestion,
    CourseRecommendation,
    EligibilityResult,
    GroundingContext,
    RetrievalCandidate,
)
from src.services.knowledge_service import (
    AnswerGenerationService,
    CatalogRetrievalService,
    CitationService,
    GroundingService,
    IntentClassificationService,
)

class PrerequisiteEvaluationService:
    """Evaluates prerequisite and corequisite eligibility for students."""
    def __init__(
        self,
        academic_record_repository: AcademicRecordRepository,
        requirement_repository: CourseRequirementRepository,
    ) -> None:
        self.academic_record_repository = academic_record_repository
        self.requirement_repository = requirement_repository

    def evaluate_course_eligibility(
        self, user_id: str, course_code: str
    ) -> EligibilityResult:
        raise NotImplementedError(
            "TODO: implement PrerequisiteEvaluationService.evaluate_course_eligibility"
        )

    def list_missing_requirements(self, user_id: str, course_code: str) -> list[str]:
        raise NotImplementedError(
            "TODO: implement PrerequisiteEvaluationService.list_missing_requirements"
        )

class CourseRecommendationService:
    """Ranks and explains course recommendations for advising questions."""
    def __init__(
        self, prerequisite_service: PrerequisiteEvaluationService
    ) -> None:
        self.prerequisite_service = prerequisite_service

    def recommend_next_courses(
        self,
        user_id: str,
        question: str,
        candidates: list[RetrievalCandidate],
        max_recommendations: int = 5,
    ) -> list[CourseRecommendation]:
        raise NotImplementedError(
            "TODO: implement CourseRecommendationService.recommend_next_courses"
        )

    def rank_recommendations(
        self, recommendations: list[CourseRecommendation]
    ) -> list[CourseRecommendation]:
        raise NotImplementedError(
            "TODO: implement CourseRecommendationService.rank_recommendations"
        )

    def explain_recommendations(
        self, recommendations: list[CourseRecommendation]
    ) -> list[CourseRecommendation]:
        raise NotImplementedError(
            "TODO: implement CourseRecommendationService.explain_recommendations"
        )

class AdvisingService:
    """Top-level orchestration service for grounded advising responses."""
    def __init__(
        self,
        intent_service: IntentClassificationService,
        retrieval_service: CatalogRetrievalService,
        grounding_service: GroundingService,
        generation_service: AnswerGenerationService,
        citation_service: CitationService,
        recommendation_service: CourseRecommendationService,
        chat_history_service: ChatHistoryService,
        unit_of_work: UnitOfWork,
    ) -> None:
        self.intent_service = intent_service
        self.retrieval_service = retrieval_service
        self.grounding_service = grounding_service
        self.generation_service = generation_service
        self.citation_service = citation_service
        self.recommendation_service = recommendation_service
        self.chat_history_service = chat_history_service
        self.unit_of_work = unit_of_work

    async def answer_question(self, request: AdvisingQuestion) -> AdvisingAnswer:
        response = await self._answer_question_without_persistence(request=request)
        with self.unit_of_work:
            self._persist_answer_in_transaction(request=request, response=response)
        return response

    async def stream_answer(self, request: AdvisingQuestion) -> AsyncIterator[str]:
        raise NotImplementedError("TODO: implement AdvisingService.stream_answer")

    def build_grounding_context(
        self, request: AdvisingQuestion, intent: str, candidates: list[RetrievalCandidate]
    ) -> GroundingContext:
        raise NotImplementedError("TODO: implement AdvisingService.build_grounding_context")

    async def _answer_question_without_persistence(
        self, request: AdvisingQuestion
    ) -> AdvisingAnswer:
        raise NotImplementedError(
            "TODO: implement AdvisingService._answer_question_without_persistence"
        )

    def _persist_answer_in_transaction(
        self, request: AdvisingQuestion, response: AdvisingAnswer
    ) -> None:
        raise NotImplementedError(
            "TODO: implement AdvisingService._persist_answer_in_transaction"
        )