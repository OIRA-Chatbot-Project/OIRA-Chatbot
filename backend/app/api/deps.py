"""
Dependency injection factories for FastAPI.

Singletons (process lifetime): get_chroma_repo, get_rag_pipeline, get_memory_service
Per-request: all repo and service factories — share a single `db` session per request
via FastAPI's Depends() cache.
"""
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.data.database import get_db
from app.data.repositories.user_repository import SQLUserRepository
from app.data.repositories.session_repository import SQLSessionRepository
from app.data.repositories.message_repository import SQLMessageRepository
from app.data.repositories.feedback_repository import SQLFeedbackRepository
from app.data.vector_store.chroma_repository import ChromaRepository
from app.services.user_service import UserService
from app.services.session_service import SessionService
from app.services.message_service import MessageService
from app.services.chat_service import ChatService
from app.services.feedback_service import FeedbackService
from app.services.schedule_service import ScheduleService
from app.services.document_service import DocumentService
from app.services.llm.rag_pipeline import RagPipeline
from app.services.llm.memory import MemoryService
from app.core import config


# ---------------------------------------------------------------------------
# Process-lifetime singletons
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_chroma_repo() -> ChromaRepository:
    return ChromaRepository(
        collection_name=config.CHROMA_COLLECTION_NAME,
        persist_directory=config.CHROMA_PATH,
        embedding_model=config.EMBEDDING_MODEL,
    )


@lru_cache(maxsize=1)
def get_rag_pipeline() -> RagPipeline:
    return RagPipeline(get_chroma_repo())


@lru_cache(maxsize=1)
def get_memory_service() -> MemoryService:
    from langchain_openai import ChatOpenAI
    decompose_llm = ChatOpenAI(temperature=0.1, model=config.OPENAI_LIGHT_MODEL)
    return MemoryService(decompose_llm)


# ---------------------------------------------------------------------------
# Per-request repositories (share the same `db` session within one request)
# ---------------------------------------------------------------------------

def get_user_repo(db: Session = Depends(get_db)) -> SQLUserRepository:
    return SQLUserRepository(db)


def get_session_repo(db: Session = Depends(get_db)) -> SQLSessionRepository:
    return SQLSessionRepository(db)


def get_message_repo(db: Session = Depends(get_db)) -> SQLMessageRepository:
    return SQLMessageRepository(db)


def get_feedback_repo(db: Session = Depends(get_db)) -> SQLFeedbackRepository:
    return SQLFeedbackRepository(db)


# ---------------------------------------------------------------------------
# Per-request services
# ---------------------------------------------------------------------------

def get_user_service(
    user_repo: SQLUserRepository = Depends(get_user_repo),
) -> UserService:
    return UserService(user_repo)


def get_session_service(
    session_repo: SQLSessionRepository = Depends(get_session_repo),
) -> SessionService:
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(temperature=0.3, model=config.OPENAI_MODEL)
    return SessionService(session_repo, llm)


def get_message_service(
    message_repo: SQLMessageRepository = Depends(get_message_repo),
    feedback_repo: SQLFeedbackRepository = Depends(get_feedback_repo),
) -> MessageService:
    return MessageService(message_repo, feedback_repo)


def get_chat_service(
    user_repo: SQLUserRepository = Depends(get_user_repo),
    session_repo: SQLSessionRepository = Depends(get_session_repo),
    message_repo: SQLMessageRepository = Depends(get_message_repo),
    feedback_repo: SQLFeedbackRepository = Depends(get_feedback_repo),
    rag: RagPipeline = Depends(get_rag_pipeline),
    memory: MemoryService = Depends(get_memory_service),
) -> ChatService:
    return ChatService(user_repo, session_repo, message_repo, feedback_repo, rag, memory)


def get_feedback_service(
    feedback_repo: SQLFeedbackRepository = Depends(get_feedback_repo),
    session_repo: SQLSessionRepository = Depends(get_session_repo),
    message_repo: SQLMessageRepository = Depends(get_message_repo),
) -> FeedbackService:
    return FeedbackService(feedback_repo, session_repo, message_repo)


def get_schedule_service(
    session_repo: SQLSessionRepository = Depends(get_session_repo),
    message_repo: SQLMessageRepository = Depends(get_message_repo),
    rag: RagPipeline = Depends(get_rag_pipeline),
) -> ScheduleService:
    return ScheduleService(session_repo, message_repo, rag)


def get_document_service() -> DocumentService:
    return DocumentService()
