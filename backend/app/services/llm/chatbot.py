"""
Thin ChatbotService wrapper for backward compatibility.

Routes that still import `get_chatbot_service` from the old location
will get this wrapper, which delegates to RagPipeline + MemoryService.
New code should inject RagPipeline and MemoryService directly via deps.py.
"""
from functools import lru_cache
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

from langchain_openai import ChatOpenAI

from app.core import config
from app.data.vector_store.chroma_repository import ChromaRepository
from app.services.llm.rag_pipeline import RagPipeline
from app.services.llm.memory import MemoryService


class ChatbotService:
    """Backward-compatible facade delegating to RagPipeline and MemoryService."""

    def __init__(self) -> None:
        self._chroma = ChromaRepository(
            collection_name=config.CHROMA_COLLECTION_NAME,
            persist_directory=config.CHROMA_PATH,
            embedding_model=config.EMBEDDING_MODEL,
        )
        self._rag = RagPipeline(self._chroma)
        self._decompose_llm = ChatOpenAI(
            temperature=0.1,
            model=config.OPENAI_LIGHT_MODEL,
        )
        self._memory = MemoryService(self._decompose_llm)

    # ------------------------------------------------------------------
    # RAG delegation
    # ------------------------------------------------------------------

    def get_answer(
        self,
        question: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        conversation_summary: Optional[str] = None,
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, List[dict], str, List[str]]:
        return self._rag.get_answer(
            question,
            conversation_history,
            conversation_summary=conversation_summary,
            user_profile=user_profile,
        )

    async def get_answer_async(
        self,
        question: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        conversation_summary: Optional[str] = None,
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, List[dict], str, List[str]]:
        return await self._rag.get_answer_async(
            question,
            conversation_history,
            conversation_summary=conversation_summary,
            user_profile=user_profile,
        )

    async def get_answer_streaming(
        self,
        question: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        conversation_summary: Optional[str] = None,
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[str]:
        async for event in self._rag.get_answer_streaming(
            question,
            conversation_history,
            conversation_summary=conversation_summary,
            user_profile=user_profile,
        ):
            yield event

    def recommend_courses_from_schedule(
        self,
        schedule_summary: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Tuple[str, List[dict], str, List[str]]:
        return self._rag.recommend_courses_from_schedule(
            schedule_summary, conversation_history
        )

    # ------------------------------------------------------------------
    # Memory delegation (kept for old callers in routes/chat.py shim)
    # ------------------------------------------------------------------

    async def _extract_user_facts(
        self,
        user_message: str,
        existing_facts: Dict[str, Any],
    ) -> Dict[str, Any]:
        return await self._memory._extract_user_facts(user_message, existing_facts)

    async def _summarize_conversation(
        self,
        session_id: str,
        existing_summary: Optional[str],
        messages_to_summarize: List[Dict[str, str]],
    ) -> str:
        return await self._memory._summarize_conversation(
            session_id, existing_summary, messages_to_summarize
        )


# ---------------------------------------------------------------------------
# Singleton factory — preserved for backward-compatible callers
# ---------------------------------------------------------------------------

_instance: Optional[ChatbotService] = None


def get_chatbot_service() -> ChatbotService:
    """Return the process-lifetime ChatbotService singleton."""
    global _instance
    if _instance is None:
        _instance = ChatbotService()
    return _instance


@lru_cache(maxsize=1)
def get_rag_pipeline() -> RagPipeline:
    """Return the process-lifetime RagPipeline singleton (for DI in deps.py)."""
    chroma = ChromaRepository(
        collection_name=config.CHROMA_COLLECTION_NAME,
        persist_directory=config.CHROMA_PATH,
        embedding_model=config.EMBEDDING_MODEL,
    )
    return RagPipeline(chroma)


@lru_cache(maxsize=1)
def get_memory_service() -> MemoryService:
    """Return the process-lifetime MemoryService singleton (for DI in deps.py)."""
    decompose_llm = ChatOpenAI(
        temperature=0.1,
        model=config.OPENAI_LIGHT_MODEL,
    )
    return MemoryService(decompose_llm)
