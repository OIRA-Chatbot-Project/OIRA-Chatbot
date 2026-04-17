from __future__ import annotations
from functools import lru_cache
from src.repository.course_repository import (
    CatalogDocumentRepository,
    CourseRepository,
    CourseRequirementRepository,
)
from src.repository.knowledge_repository import CatalogVectorRepository
from src.repository.message_repository import ChatMessageRepository, ChatSessionRepository
from src.repository.unit_of_work import NoOpUnitOfWork, UnitOfWork
from src.repository.user_repository import (
    AcademicRecordRepository,
    FeedbackRepository,
    UserRepository,
)
from src.services.advising_service import (
    AdvisingService,
    CourseRecommendationService,
    PrerequisiteEvaluationService,
)
from src.services.chat_service import ChatHistoryService
from src.services.document_service import CatalogIngestionService
from src.services.knowledge_service import (
    AnswerGenerationService,
    CatalogRetrievalService,
    CitationService,
    GroundingService,
    IntentClassificationService,
)
from src.services.user_service import UserService

@lru_cache
def get_course_repository() -> CourseRepository:
    return CourseRepository()

@lru_cache
def get_course_requirement_repository() -> CourseRequirementRepository:
    return CourseRequirementRepository()

@lru_cache
def get_catalog_document_repository() -> CatalogDocumentRepository:
    return CatalogDocumentRepository()

@lru_cache
def get_catalog_vector_repository() -> CatalogVectorRepository:
    return CatalogVectorRepository()

@lru_cache
def get_chat_session_repository() -> ChatSessionRepository:
    return ChatSessionRepository()

@lru_cache
def get_chat_message_repository() -> ChatMessageRepository:
    return ChatMessageRepository()

@lru_cache
def get_user_repository() -> UserRepository:
    return UserRepository()

@lru_cache
def get_academic_record_repository() -> AcademicRecordRepository:
    return AcademicRecordRepository()

@lru_cache
def get_feedback_repository() -> FeedbackRepository:
    return FeedbackRepository()


@lru_cache
def get_unit_of_work() -> UnitOfWork:
    return NoOpUnitOfWork()

@lru_cache
def get_intent_classification_service() -> IntentClassificationService:
    return IntentClassificationService()

@lru_cache
def get_catalog_retrieval_service() -> CatalogRetrievalService:
    return CatalogRetrievalService(
        course_repository=get_course_repository(),
        vector_repository=get_catalog_vector_repository(),
    )

@lru_cache
def get_grounding_service() -> GroundingService:
    return GroundingService()

@lru_cache
def get_answer_generation_service() -> AnswerGenerationService:
    return AnswerGenerationService()

@lru_cache
def get_citation_service() -> CitationService:
    return CitationService()

@lru_cache
def get_prerequisite_evaluation_service() -> PrerequisiteEvaluationService:
    return PrerequisiteEvaluationService(
        academic_record_repository=get_academic_record_repository(),
        requirement_repository=get_course_requirement_repository(),
    )

@lru_cache
def get_course_recommendation_service() -> CourseRecommendationService:
    return CourseRecommendationService(
        prerequisite_service=get_prerequisite_evaluation_service()
    )

@lru_cache
def get_chat_history_service() -> ChatHistoryService:
    return ChatHistoryService(
        session_repository=get_chat_session_repository(),
        message_repository=get_chat_message_repository(),
        unit_of_work=get_unit_of_work(),
    )

@lru_cache
def get_catalog_ingestion_service() -> CatalogIngestionService:
    return CatalogIngestionService(
        document_repository=get_catalog_document_repository(),
        course_repository=get_course_repository(),
        vector_repository=get_catalog_vector_repository(),
        unit_of_work=get_unit_of_work(),
    )

@lru_cache
def get_user_service() -> UserService:
    return UserService(
        user_repository=get_user_repository(),
        academic_record_repository=get_academic_record_repository(),
        feedback_repository=get_feedback_repository(),
        unit_of_work=get_unit_of_work(),
    )

@lru_cache
def get_advising_service() -> AdvisingService:
    return AdvisingService(
        intent_service=get_intent_classification_service(),
        retrieval_service=get_catalog_retrieval_service(),
        grounding_service=get_grounding_service(),
        generation_service=get_answer_generation_service(),
        citation_service=get_citation_service(),
        recommendation_service=get_course_recommendation_service(),
        chat_history_service=get_chat_history_service(),
        unit_of_work=get_unit_of_work(),
    )
