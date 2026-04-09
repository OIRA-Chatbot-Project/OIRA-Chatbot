"""
MemoryService: background user-fact extraction and conversation summarization.

Opens its own DB session — never shares the request-scoped session.
All exceptions are caught and logged; they never bubble up to the caller.
"""
import asyncio
import json
from typing import Any, Dict, List, Optional

from langchain_openai import ChatOpenAI

from app.core import config


class MemoryService:
    def __init__(self, decompose_llm: ChatOpenAI) -> None:
        self.decompose_llm = decompose_llm

    async def run_post_response_tasks(
        self,
        session_id: str,
        user_message_content: str,
        clerk_user_id: str,
    ) -> None:
        """Run background memory tasks after a response is sent.

        1. Extracts persistent user facts and saves them to User.profile_facts.
        2. If the session message count exceeds SUMMARY_WINDOW_SIZE, summarizes
           older messages into Session.conversation_summary.

        Opens its own DB connection — never shares the request-scoped session.
        All exceptions are caught and logged.
        """
        if not config.ENABLE_CONVERSATION_MEMORY:
            return

        # Import here to avoid circular imports at module load time
        from app.data.database import SessionLocal
        from app.data.models.user import User
        from app.data.models.session import Session
        from app.data.models.message import Message

        db = SessionLocal()
        try:
            # --- Fact extraction ---
            user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()
            if user:
                existing_facts: Dict[str, Any] = {}
                if user.profile_facts:
                    try:
                        existing_facts = json.loads(user.profile_facts)
                    except json.JSONDecodeError:
                        existing_facts = {}

                updated_facts = await self._extract_user_facts(user_message_content, existing_facts)
                if updated_facts != existing_facts:
                    user.profile_facts = json.dumps(updated_facts)
                    db.commit()

            # --- Summarization ---
            total_count = (
                db.query(Message).filter(Message.session_id == session_id).count()
            )

            if total_count > config.SUMMARY_WINDOW_SIZE:
                session_obj = (
                    db.query(Session).filter(Session.session_id == session_id).first()
                )
                if session_obj:
                    messages_to_keep = (
                        db.query(Message)
                        .filter(Message.session_id == session_id)
                        .order_by(Message.created_at.desc())
                        .limit(config.SUMMARY_WINDOW_SIZE)
                        .all()
                    )
                    keep_ids = {m.id for m in messages_to_keep}
                    older_messages = (
                        db.query(Message)
                        .filter(
                            Message.session_id == session_id,
                            ~Message.id.in_(keep_ids),
                        )
                        .order_by(Message.created_at.asc())
                        .all()
                    )
                    messages_to_summarize = [
                        {"role": m.role, "content": m.content} for m in older_messages
                    ]
                    existing_summary = session_obj.conversation_summary or None
                    new_summary = await self._summarize_conversation(
                        session_id, existing_summary, messages_to_summarize
                    )
                    if new_summary and new_summary != existing_summary:
                        session_obj.conversation_summary = new_summary
                        db.commit()

        except Exception as e:
            print(f"[WARNING] Background memory task failed for session {session_id}: {e}")
        finally:
            db.close()

    async def _summarize_conversation(
        self,
        session_id: str,
        existing_summary: Optional[str],
        messages_to_summarize: List[Dict[str, str]],
    ) -> str:
        """Compress older messages into a brief summary paragraph."""
        if not messages_to_summarize:
            return existing_summary or ""

        history_text = "\n".join(
            f"{m['role'].capitalize()}: {m['content']}" for m in messages_to_summarize
        )

        if existing_summary:
            prompt = (
                "You are summarizing a student–assistant chat session. "
                "Below is a prior summary and additional messages. "
                "Produce a single updated 3–6 sentence third-person paragraph that incorporates both. "
                "Capture: topics asked, key facts the student mentioned, decisions or clarifications made. "
                "Return ONLY the paragraph, no preamble.\n\n"
                f"PRIOR SUMMARY:\n{existing_summary}\n\n"
                f"NEW MESSAGES:\n{history_text}"
            )
        else:
            prompt = (
                "You are summarizing a student–assistant chat session. "
                "Write a 3–6 sentence third-person paragraph capturing: "
                "topics asked, key facts the student mentioned, decisions or clarifications made. "
                "Return ONLY the paragraph, no preamble.\n\n"
                f"MESSAGES:\n{history_text}"
            )

        try:
            response = await asyncio.to_thread(self.decompose_llm.invoke, prompt)
            result = (response.content or "").strip()
            if result:
                print(f"[MEMORY] Session {session_id}: summary updated ({len(result)} chars)")
                return result
        except Exception as e:
            print(f"[WARNING] Summarization failed for session {session_id}: {e}")

        return existing_summary or ""

    async def _extract_user_facts(
        self,
        user_message: str,
        existing_facts: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Extract and merge persistent user facts from a single message."""
        prompt = (
            "You extract persistent facts about a Bucknell University user from a single message.\n\n"
            "STEP 1 – Detect user type from context clues (words like 'I am a professor', "
            "'as a student', 'I advise students', 'in my department', etc.).\n"
            "Set 'user_type' to one of: student, faculty, advisor, staff, unknown.\n\n"
            "STEP 2 – Extract only the facts that are explicitly stated. "
            "For students: major, minor, concentration, year (freshman/sophomore/junior/senior), "
            "college, completed_courses (comma-separated course codes), interests, advisor.\n"
            "For faculty/advisor/staff: department, role_title, interests.\n\n"
            "Rules:\n"
            "- Return {} if nothing relevant is found.\n"
            "- All keys are optional; only include what is explicitly stated.\n"
            "- Return ONLY valid JSON, no explanation.\n\n"
            f"MESSAGE:\n{user_message}"
        )

        try:
            response = await asyncio.to_thread(self.decompose_llm.invoke, prompt)
            raw = (response.content or "").strip()
            json_start = raw.find("{")
            json_end = raw.rfind("}") + 1
            if json_start < 0 or json_end <= json_start:
                return existing_facts
            new_facts: Dict[str, Any] = json.loads(raw[json_start:json_end])
            if not new_facts:
                return existing_facts

            merged: Dict[str, Any] = {**existing_facts, **new_facts}

            # List-type fields: union rather than replace
            for list_key in ("completed_courses", "interests"):
                old_val = existing_facts.get(list_key, "")
                new_val = new_facts.get(list_key, "")
                if old_val and new_val:
                    merged[list_key] = ", ".join(
                        sorted(
                            {c.strip().upper() for c in str(old_val).split(",")}
                            | {c.strip().upper() for c in str(new_val).split(",")}
                        )
                    )

            print(f"[MEMORY] User facts updated: {list(merged.keys())}")
            return merged

        except (json.JSONDecodeError, Exception) as e:
            print(f"[WARNING] User fact extraction failed: {e}")
            return existing_facts
