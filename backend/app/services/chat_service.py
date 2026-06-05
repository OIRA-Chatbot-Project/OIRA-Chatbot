"""
ChatService: orchestrates chat, regenerate, and streaming endpoints.
Extracted from the 686-line routes/chat.py.
"""
import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import AsyncIterator, Dict, List, Optional, Any

from fastapi import HTTPException

from app.data.repositories.user_repository import SQLUserRepository
from app.data.repositories.session_repository import SQLSessionRepository
from app.data.repositories.message_repository import SQLMessageRepository
from app.data.repositories.feedback_repository import SQLFeedbackRepository
from app.services.llm.rag_pipeline import RagPipeline
from app.services.llm.memory import MemoryService


@dataclass
class ChatResult:
    message_id: int
    answer: str
    citations: List[dict]
    question_category: str
    follow_ups: List[str]
    session_id: str
    user_message_id: Optional[int] = None


@dataclass
class StreamContext:
    user_message_id: int
    message: str
    conversation_history: List[Dict[str, str]]
    session_summary: Optional[str]
    user_profile: Optional[Dict[str, Any]]
    session_id: str
    clerk_user_id: str


class ChatService:
    def __init__(
        self,
        user_repo: SQLUserRepository,
        session_repo: SQLSessionRepository,
        message_repo: SQLMessageRepository,
        feedback_repo: SQLFeedbackRepository,
        rag: RagPipeline,
        memory: MemoryService,
    ) -> None:
        self.user_repo = user_repo
        self.session_repo = session_repo
        self.message_repo = message_repo
        self.feedback_repo = feedback_repo
        self.rag = rag
        self.memory = memory

    # ------------------------------------------------------------------
    # Non-streaming chat
    # ------------------------------------------------------------------

    async def handle_chat(
        self,
        session_id: str,
        message: str,
        clerk_user_id: str,
    ) -> ChatResult:
        user = self.user_repo.get_by_clerk_id(clerk_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found. Please sign up first.")

        session = self.session_repo.get_or_create_for_user(session_id, user.id)

        user_msg = self.message_repo.create(session_id=session_id, role="user", content=message)

        conversation_history = self._load_history(session_id, before_id=user_msg.id)
        session_summary, user_profile = self._load_memory_context(session, user)

        answer, citations, question_category, followups = await self.rag.get_answer_async(
            message,
            conversation_history,
            conversation_summary=session_summary,
            user_profile=user_profile or None,
        )

        cleaned = self._clean_answer(answer)
        assistant_msg = self.message_repo.create(
            session_id=session_id,
            role="assistant",
            content=cleaned,
            citations=json.dumps(citations),
        )

        self.schedule_post_response_tasks(session_id, message, clerk_user_id)

        return ChatResult(
            message_id=assistant_msg.id,
            user_message_id=user_msg.id,
            answer=cleaned,
            citations=citations,
            question_category=question_category,
            follow_ups=followups,
            session_id=session_id,
        )

    # ------------------------------------------------------------------
    # Non-streaming regenerate
    # ------------------------------------------------------------------

    async def handle_regenerate(
        self,
        session_id: str,
        user_message_id: int,
        clerk_user_id: str,
    ) -> ChatResult:
        user = self.user_repo.get_by_clerk_id(clerk_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found. Please sign up first.")

        session = self.session_repo.get_by_id_and_user(session_id, user.id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        user_msg = self.message_repo.get_by_id(user_message_id)
        if not user_msg or user_msg.session_id != session_id:
            raise HTTPException(status_code=404, detail="Message not found")
        if user_msg.role != "user":
            raise HTTPException(status_code=400, detail="Can only regenerate from a user message")

        deleted_ids = self.message_repo.delete_after(session_id, user_message_id)
        if deleted_ids:
            self.feedback_repo.delete_for_messages(deleted_ids)

        self.session_repo.touch(session)

        conversation_history = self._load_history(session_id, before_id=user_message_id)
        session_summary, user_profile = self._load_memory_context(session, user)

        answer, citations, question_category, followups = await self.rag.get_answer_async(
            user_msg.content,
            conversation_history,
            conversation_summary=session_summary,
            user_profile=user_profile or None,
        )

        cleaned = self._clean_answer(answer)
        assistant_msg = self.message_repo.create(
            session_id=session_id,
            role="assistant",
            content=cleaned,
            citations=json.dumps(citations),
        )

        self.schedule_post_response_tasks(session_id, user_msg.content, clerk_user_id)

        return ChatResult(
            message_id=assistant_msg.id,
            answer=cleaned,
            citations=citations,
            question_category=question_category,
            follow_ups=followups,
            session_id=session_id,
        )

    # ------------------------------------------------------------------
    # Streaming helpers
    # ------------------------------------------------------------------

    async def prepare_stream(
        self,
        session_id: str,
        message: str,
        clerk_user_id: str,
    ) -> StreamContext:
        """Load context and persist the user message; return a StreamContext for the generator."""
        user = self.user_repo.get_by_clerk_id(clerk_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found. Please sign up first.")

        session = self.session_repo.get_or_create_for_user(session_id, user.id)

        user_msg = self.message_repo.create(session_id=session_id, role="user", content=message)

        conversation_history = self._load_history(session_id, before_id=user_msg.id)
        session_summary, user_profile = self._load_memory_context(session, user)

        return StreamContext(
            user_message_id=user_msg.id,
            message=message,
            conversation_history=conversation_history,
            session_summary=session_summary,
            user_profile=user_profile,
            session_id=session_id,
            clerk_user_id=clerk_user_id,
        )

    async def prepare_regenerate_stream(
        self,
        session_id: str,
        user_message_id: int,
        clerk_user_id: str,
    ) -> StreamContext:
        """Delete messages after target; return a StreamContext for the regenerate generator."""
        user = self.user_repo.get_by_clerk_id(clerk_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found. Please sign up first.")

        session = self.session_repo.get_by_id_and_user(session_id, user.id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        user_msg = self.message_repo.get_by_id(user_message_id)
        if not user_msg or user_msg.session_id != session_id:
            raise HTTPException(status_code=404, detail="Message not found")
        if user_msg.role != "user":
            raise HTTPException(status_code=400, detail="Can only regenerate from a user message")

        deleted_ids = self.message_repo.delete_after(session_id, user_message_id)
        if deleted_ids:
            self.feedback_repo.delete_for_messages(deleted_ids)

        self.session_repo.touch(session)

        conversation_history = self._load_history(session_id, before_id=user_message_id)
        session_summary, user_profile = self._load_memory_context(session, user)

        return StreamContext(
            user_message_id=user_message_id,
            message=user_msg.content,
            conversation_history=conversation_history,
            session_summary=session_summary,
            user_profile=user_profile,
            session_id=session_id,
            clerk_user_id=clerk_user_id,
        )

    async def stream_events(self, context: StreamContext) -> AsyncIterator[str]:
        """Async generator: yields SSE events from RAG, then saves the message to DB."""
        final_answer = ""
        final_citations: List[dict] = []

        try:
            user_payload = json.dumps({"message_id": context.user_message_id})
            yield f"event: user\ndata: {user_payload}\n\n"

            async for event in self.rag.get_answer_streaming(
                context.message,
                context.conversation_history,
                conversation_summary=context.session_summary,
                user_profile=context.user_profile or None,
            ):
                yield event

                if event.startswith("event: done"):
                    data_line = event.split("data: ", 1)[1].split("\n")[0]
                    done_data = json.loads(data_line)
                    final_answer = done_data.get("answer", "")
                    final_citations = done_data.get("citations", [])

        except Exception as e:
            print(f"[ERROR] Streaming error: {e}")
            error_payload = json.dumps({"error": str(e)})
            yield f"event: error\ndata: {error_payload}\n\n"
            return

        try:
            cleaned = self._clean_answer(final_answer)
            assistant_msg = self.message_repo.create(
                session_id=context.session_id,
                role="assistant",
                content=cleaned,
                citations=json.dumps(final_citations),
            )

            saved_payload = json.dumps({"message_id": assistant_msg.id})
            yield f"event: saved\ndata: {saved_payload}\n\n"

            self.schedule_post_response_tasks(
                context.session_id, context.message, context.clerk_user_id
            )
        except Exception as e:
            print(f"[ERROR] DB save error after stream: {e}")
            error_payload = json.dumps({"error": "Failed to save message"})
            yield f"event: error\ndata: {error_payload}\n\n"

    async def regenerate_stream_events(self, context: StreamContext) -> AsyncIterator[str]:
        """Async generator: yields SSE events for regenerate, then saves to DB."""
        final_answer = ""
        final_citations: List[dict] = []

        try:
            async for event in self.rag.get_answer_streaming(
                context.message,
                context.conversation_history,
                conversation_summary=context.session_summary,
                user_profile=context.user_profile or None,
            ):
                yield event

                if event.startswith("event: done"):
                    data_line = event.split("data: ", 1)[1].split("\n")[0]
                    done_data = json.loads(data_line)
                    final_answer = done_data.get("answer", "")
                    final_citations = done_data.get("citations", [])

        except Exception as e:
            print(f"[ERROR] Regenerate streaming error: {e}")
            error_payload = json.dumps({"error": str(e)})
            yield f"event: error\ndata: {error_payload}\n\n"
            return

        try:
            cleaned = self._clean_answer(final_answer)
            assistant_msg = self.message_repo.create(
                session_id=context.session_id,
                role="assistant",
                content=cleaned,
                citations=json.dumps(final_citations),
            )

            saved_payload = json.dumps({"message_id": assistant_msg.id})
            yield f"event: saved\ndata: {saved_payload}\n\n"

            self.schedule_post_response_tasks(
                context.session_id, context.message, context.clerk_user_id
            )
        except Exception as e:
            print(f"[ERROR] DB save error after regenerate stream: {e}")
            error_payload = json.dumps({"error": "Failed to save message"})
            yield f"event: error\ndata: {error_payload}\n\n"

    def schedule_post_response_tasks(
        self,
        session_id: str,
        user_message_content: str,
        clerk_user_id: str,
    ) -> None:
        """Fire-and-forget: schedule background memory tasks."""
        asyncio.create_task(
            self.memory.run_post_response_tasks(
                session_id=session_id,
                user_message_content=user_message_content,
                clerk_user_id=clerk_user_id,
            )
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_history(self, session_id: str, before_id: int) -> List[Dict[str, str]]:
        msgs = self.message_repo.get_history_before(session_id, before_id, limit=6)
        return [{"role": m.role, "content": m.content} for m in msgs]

    def _load_memory_context(self, session: Any, user: Any):
        session_summary: Optional[str] = getattr(session, "conversation_summary", None) or None

        user_profile: Dict[str, Any] = {}
        profile_facts = getattr(user, "profile_facts", None)
        if profile_facts:
            try:
                user_profile = json.loads(profile_facts)
            except json.JSONDecodeError:
                user_profile = {}

        return session_summary, user_profile

    @staticmethod
    def _clean_answer(answer: str) -> str:
        """Remove inline bracket citations and normalize spacing."""
        try:
            cleaned = re.sub(r"\[[^\]]+?,\s*p\.\s*\d+\]", "", answer)
            cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
            cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
            cleaned = re.sub(r"(?<=\S)[ \t]{2,}", " ", cleaned)
            return cleaned.strip()
        except Exception:
            return answer
