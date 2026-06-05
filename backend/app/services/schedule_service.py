"""
ScheduleService: schedule upload processing and course recommendations.
"""
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from app.data.repositories.session_repository import SQLSessionRepository
from app.data.repositories.message_repository import SQLMessageRepository
from app.data.repositories.user_repository import SQLUserRepository
from app.services.llm.rag_pipeline import RagPipeline


@dataclass
class ScheduleResult:
    message_id: int
    answer: str
    citations: List[dict]
    session_id: str
    schedule_summary: str
    parsed_courses: List[dict]
    schedule_message_id: int
    question_category: str
    follow_ups: List[str]


class ScheduleService:
    def __init__(
        self,
        session_repo: SQLSessionRepository,
        message_repo: SQLMessageRepository,
        rag: RagPipeline,
    ) -> None:
        self.session_repo = session_repo
        self.message_repo = message_repo
        self.rag = rag

    def process_upload(
        self,
        session_id: str,
        clerk_user_id: str,
        file_content: bytes,
        filename: str,
        user_repo: SQLUserRepository,
    ) -> ScheduleResult:
        from app.services.schedule_parser import (
            extract_text_from_upload,
            parse_schedule_entries,
            summarize_schedule,
        )

        user = user_repo.get_by_clerk_id(clerk_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found. Please sign up first.")

        session = self.session_repo.get_or_create_for_user(session_id, user.id)

        if not file_content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        try:
            raw_text = extract_text_from_upload(file_content, filename)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        parsed_courses = parse_schedule_entries(raw_text)
        if not parsed_courses:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Could not detect any courses in the uploaded schedule. "
                    "Please try a clearer image or a text export."
                ),
            )

        summary = summarize_schedule(parsed_courses)

        user_msg = self.message_repo.create(
            session_id=session_id,
            role="user",
            content=f"Schedule uploaded:\n{summary}",
        )

        history_msgs = self.message_repo.get_history_before(
            session_id, before_id=user_msg.id, limit=6
        )
        conversation_history = [{"role": m.role, "content": m.content} for m in history_msgs]

        answer, citations, question_category, followups = self.rag.recommend_courses_from_schedule(
            summary, conversation_history
        )

        cleaned = self._clean_answer(answer)
        assistant_msg = self.message_repo.create(
            session_id=session_id,
            role="assistant",
            content=cleaned,
            citations=json.dumps(citations),
        )

        return ScheduleResult(
            message_id=assistant_msg.id,
            answer=answer,
            citations=citations,
            session_id=session_id,
            schedule_summary=summary,
            parsed_courses=parsed_courses,
            schedule_message_id=user_msg.id,
            question_category=question_category,
            follow_ups=followups,
        )

    @staticmethod
    def _clean_answer(answer: str) -> str:
        try:
            cleaned = re.sub(r"\[[^\]]+?,\s*p\.\s*\d+\]", "", answer)
            cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
            cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
            return cleaned.strip()
        except Exception:
            return answer
