"""
RagPipeline: all retrieval-augmented generation logic.

Extracted from services/chatbot_service.py. Receives a ChromaRepository
so the vector store is a proper injectable dependency.
"""
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from typing import List, Dict, Tuple, Optional, Any
import asyncio
import os
import re
import json

from app.core import config
from app.data.vector_store.chroma_repository import ChromaRepository
from app.services.llm.prompts import (
    get_decompose_prompt,
    get_user_prompt,
    get_contextualize_prompt,
    get_question_classifier_prompt,
    get_conversational_prompt,
    SYSTEM_PROMPT,
    CONVERSATIONAL_SYSTEM_PROMPT,
    CATALOG_SYSTEM_PROMPT,
    POLICY_SYSTEM_PROMPT,
)


class RagPipeline:
    """RAG pipeline: classification → decomposition → retrieval → generation."""

    def __init__(self, chroma: ChromaRepository) -> None:
        self.chroma = chroma

        self.llm = ChatOpenAI(
            temperature=0.3,
            model=config.OPENAI_MODEL,
        )
        self.decompose_llm = ChatOpenAI(
            temperature=0.1,
            model=config.OPENAI_LIGHT_MODEL,
        )
        self.classifier_llm = ChatOpenAI(
            temperature=config.QUESTION_CLASSIFIER_TEMPERATURE,
            model=config.OPENAI_LIGHT_MODEL,
        )

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _short_source(self, path: str) -> str:
        if not path:
            return "Source"
        return os.path.basename(path).replace("_", " ")

    def _normalize_text(self, text: str) -> str:
        if not text:
            return text
        return re.sub(r"\s+([,.;:!?])", r"\1", text)

    def _format_history_context(self, conversation_history: List[Dict[str, str]]) -> str:
        """Format conversation history into a concise string for LLM prompts."""
        if not conversation_history:
            return ""
        return "\n".join(
            f"{msg['role'].capitalize()}: {msg['content'][:150]}"
            for msg in conversation_history[-6:]
        )

    # ── Classification ────────────────────────────────────────────────────────

    def _classify_question(
        self,
        question: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        if not config.ENABLE_OFF_TOPIC_DETECTION:
            return "course_catalog"

        history_text = self._format_history_context(conversation_history or [])
        classifier_prompt = get_question_classifier_prompt(question, history_text)

        try:
            response = self.classifier_llm.invoke(classifier_prompt)
            response_text = response.content.strip()

            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(response_text[json_start:json_end])
                category = data.get("category", "course_catalog")

                valid = {"course_catalog", "academic_policy", "off_topic", "greeting", "thank_you", "clarification_needed"}
                if category in valid:
                    if category == "clarification_needed" and conversation_history:
                        print("[CLASSIFICATION] 'clarification_needed' overridden to 'course_catalog' (active conversation)")
                        return "course_catalog"
                    print(f"[CLASSIFICATION] Question classified as: {category}")
                    return category
                print(f"[WARNING] Invalid category '{category}', defaulting to 'course_catalog'")

        except (json.JSONDecodeError, KeyError, AttributeError) as e:
            print(f"[WARNING] Question classification failed: {e}. Defaulting to 'course_catalog'")

        return "course_catalog"

    def _get_system_prompt(self, question_category: str) -> str:
        if question_category == "course_catalog":
            return CATALOG_SYSTEM_PROMPT
        if question_category == "academic_policy":
            return POLICY_SYSTEM_PROMPT
        return SYSTEM_PROMPT

    def _get_llm_conversational_response(
        self,
        category: str,
        question: str,
        conversation_history: List[Dict[str, str]],
    ) -> Optional[str]:
        CONVERSATIONAL_CATEGORIES = {"greeting", "thank_you", "clarification_needed", "off_topic"}
        if category not in CONVERSATIONAL_CATEGORIES:
            return None

        user_prompt = get_conversational_prompt(category, question)
        messages = [
            SystemMessage(content=CONVERSATIONAL_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]
        try:
            response = self.decompose_llm.invoke(messages)
            return (response.content or "").strip() or None
        except Exception as e:
            print(f"[WARNING] Conversational LLM failed ({category}): {e}. Using fallback.")
            fallbacks = {
                "greeting": config.GREETING_MESSAGE,
                "thank_you": config.THANK_YOU_MESSAGE,
                "clarification_needed": config.CLARIFICATION_MESSAGE,
                "off_topic": config.OFF_TOPIC_MESSAGE,
            }
            return fallbacks.get(category)

    # ── Document utilities ─────────────────────────────────────────────────────

    def _get_document_url(
        self,
        source_filename: str,
        page: int,
        source_url: Optional[str] = None,
        doc_type: Optional[str] = None,
    ) -> Optional[str]:
        if source_url:
            return source_url
        if doc_type == "policy":
            return None
        return f"/catalog.pdf#page={page}"

    def _extract_course_codes(self, docs: List) -> List[str]:
        code_re = re.compile(r"\b[A-Z]{2,4}\s?\d{3}[A-Z]?\b")
        codes: set = set()
        for doc in docs:
            for m in code_re.finditer(doc.page_content or ""):
                code = re.sub(r"\s+", " ", m.group(0).upper()).strip()
                codes.add(code)
        return sorted(codes)

    def _enrich_with_course_entries(self, docs: List, question: str) -> List:
        if not docs or not self._is_sequence_question(question):
            return docs

        codes = self._extract_course_codes(docs)
        if not codes:
            return docs

        extra_docs = []
        for code in codes[:14]:
            variants = [code, code.replace(" ", "")]
            found = []
            for variant in variants:
                filt = {"$and": [{"doc_type": "catalog"}, {"course_code": variant}]}
                found = self.chroma.store.similarity_search(code, k=1, filter=filt)
                if found:
                    break
            if not found:
                found = self.chroma.store.similarity_search(code, k=2, filter={"doc_type": "catalog"})
            if found:
                extra_docs.extend(found)

        return self._merge_docs(docs, extra_docs) if extra_docs else docs

    def _augment_management_plan_docs(self, docs: List, question: str, search_query: str) -> List:
        if not docs or not self._is_sequence_question(question):
            return docs
        if not self._is_management_major_query(f"{search_query} {question}"):
            return docs

        augmentation_queries = [
            "Freeman College Core Requirements",
            "Freeman College of Management General Education Curriculum",
            "BSBA degree requirements",
            "FOUNDATIONAL LITERACY REQUIREMENTS",
            "MANAGERIAL LITERACY REQUIREMENTS",
            "Analytics & Operations Management Suggested Plan of Study Freeman Core Courses",
        ]
        extra_docs = []
        for query in augmentation_queries:
            found = self.chroma.store.similarity_search(query, k=2, filter={"doc_type": "catalog"})
            if found:
                extra_docs.extend(found)

        return self._merge_docs(docs, extra_docs) if extra_docs else docs

    def _dedupe_citations(self, citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen: set = set()
        deduped = []
        for c in citations:
            key = (c.get("source"), c.get("page"), c.get("content"))
            if key not in seen:
                seen.add(key)
                deduped.append(c)
        return deduped

    def _prepare_knowledge(self, docs: List) -> str:
        parts = []
        for d in docs:
            meta = d.metadata or {}
            src = self._short_source(meta.get("source", "Catalogue"))
            page = (meta.get("page", 0) or 0) + 1
            header = f"[{src}, p. {page}]"
            content = self._normalize_text(d.page_content).strip()
            parts.append(f"{header}\n{content}\n{header}\n")
        return "\n".join(parts)

    def _build_citations(self, docs: List) -> List[Dict[str, Any]]:
        citations = []
        for doc in docs:
            meta = doc.metadata or {}
            src = self._short_source(meta.get("source", "Catalogue"))
            page = (meta.get("page", 0) or 0) + 1
            source_filename = os.path.basename(meta.get("source", "catalog.pdf"))
            doc_type = meta.get("doc_type", "catalog")
            source_url = meta.get("source_url")

            if doc_type == "policy" and not source_url:
                continue

            citations.append({
                "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                "source": src,
                "page": page,
                "url": self._get_document_url(source_filename, page, source_url, doc_type),
                "doc_type": doc_type,
                "filename": source_filename,
            })
        return self._dedupe_citations(citations)

    # ── Query analysis helpers ─────────────────────────────────────────────────

    def _decompose_query(self, question: str) -> List[str]:
        decompose_prompt = get_decompose_prompt(question)
        try:
            response = self.decompose_llm.invoke(decompose_prompt)
            response_text = response.content.strip()
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(response_text[json_start:json_end])
                if data.get("type") == "simple" or not data.get("sub_questions"):
                    return [question]
                if data.get("type") == "too_broad":
                    print(f"[WARNING] Query too broad. Suggestion: {data.get('suggestion', '')}")
                    return [question]
                sub_questions = data.get("sub_questions", [])
                if isinstance(sub_questions, list) and sub_questions:
                    return sub_questions[:5]
        except (json.JSONDecodeError, KeyError, AttributeError) as e:
            print(f"[WARNING] Query decomposition failed: {e}. Using original question.")
        return [question]

    def _build_contextual_query(
        self, question: str, conversation_history: List[Dict[str, str]]
    ) -> str:
        if not conversation_history:
            return question
        recent_history = conversation_history[-6:]
        if not recent_history:
            return question
        history_text = "\n".join(
            f"{msg['role'].capitalize()}: {msg['content'][:150]}" for msg in recent_history
        )
        contextualize_prompt = get_contextualize_prompt(question, history_text)
        try:
            response = self.decompose_llm.invoke(contextualize_prompt)
            contextual_query = response.content.strip()
            if contextual_query and len(contextual_query) > 10:
                return contextual_query
        except Exception as e:
            print(f"[WARNING] Contextualization failed: {e}. Using original question.")
        return question

    def _is_simple_query(self, question: str) -> bool:
        words = question.split()
        if len(words) > config.SIMPLE_QUERY_MAX_WORDS:
            return False
        q_lower = question.lower()
        multi_part_markers = [" and ", " vs ", " versus ", "compare", "difference between", "both", "each", "as well as"]
        if any(m in q_lower for m in multi_part_markers):
            return False
        if question.count("?") > 1:
            return False
        if len(re.findall(r"[A-Z]{3,4}\s*\d{3}", question)) > 1:
            return False
        listing_patterns = [r"\b\d+\.", r"\bfirst\b", r"\bsecond\b", r"\bthird\b"]
        if any(re.search(pat, q_lower) for pat in listing_patterns):
            return False
        return True

    def _is_sequence_question(self, question: str) -> bool:
        q = question.lower()
        direct_markers = ("sequence", "four-year", "four year", "plan", "recommended sequence", "curriculum", "roadmap")
        if any(k in q for k in direct_markers):
            return True
        year_markers = ("first year", "sophomore", "junior", "senior")
        schedule_markers = ("schedule", "semester", "fall", "spring", "what should i take")
        return any(y in q for y in year_markers) and any(s in q for s in schedule_markers)

    def _is_management_major_query(self, text: str) -> bool:
        q = text.lower()
        markers = (
            "freeman", "management college", "college of management", "bsba",
            "business analytics", "anop", "accounting", "finance", "acfm",
            "mors", "mgmt", "management and organizations",
            "markets, innovation & design", "mide", "markets innovation and design",
        )
        return any(m in q for m in markers)

    def _expand_sequence_queries(self, base_query: str, question: str) -> List[str]:
        expansions = [
            base_query,
            f"{base_query} recommended sequence",
            f"{base_query} four-year plan",
            f"{base_query} major requirements",
            f"{base_query} core curriculum",
            "culminating experience",
        ]
        if self._is_management_major_query(f"{base_query} {question}"):
            expansions.extend([
                "Freeman College core curriculum",
                "BSBA core requirements",
                "Freeman College of Management general education curriculum",
                "BSBA degree requirements",
            ])
        seen: set = set()
        deduped = []
        for q in expansions:
            if q not in seen:
                seen.add(q)
                deduped.append(q)
        return deduped

    def _prioritize_sequence_queries(
        self, sub_questions: List[str], search_query: str, question: str, max_queries: int = 8
    ) -> List[str]:
        prioritized = self._expand_sequence_queries(search_query, question) + sub_questions
        seen: set = set()
        ordered = []
        for query in prioritized:
            if query not in seen:
                seen.add(query)
                ordered.append(query)
            if len(ordered) >= max_queries:
                break
        return ordered

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def _merge_docs(self, base_docs: List, extra_docs: List) -> List:
        merged = list(base_docs)
        seen = {(d.metadata.get("source", ""), d.metadata.get("page", 0)) for d in merged}
        for d in extra_docs:
            key = (d.metadata.get("source", ""), d.metadata.get("page", 0))
            if key not in seen:
                seen.add(key)
                merged.append(d)
        return merged

    def _retrieve_for_subqueries(
        self, sub_questions: List[str], doc_type_filter: Optional[str] = None
    ) -> List:
        num_subqueries = len(sub_questions)
        if not num_subqueries:
            return []

        min_per_query = config.MIN_DOCS_PER_SUBQUERY
        if min_per_query * num_subqueries > config.MAX_MULTI_STEP_DOCS:
            min_per_query = max(2, config.MAX_MULTI_STEP_DOCS // num_subqueries)

        docs_per_question = []
        for sub_q in sub_questions:
            try:
                if doc_type_filter:
                    docs = self.chroma.store.similarity_search(sub_q, k=config.RETRIEVER_K, filter={"doc_type": doc_type_filter})
                else:
                    docs = self.chroma.retriever.invoke(sub_q)
                docs_per_question.append(docs)
            except Exception as e:
                print(f"[WARNING] Retrieval failed for sub-query '{sub_q}': {e}")
                docs_per_question.append([])

        return self._merge_retrieved(docs_per_question, min_per_query, num_subqueries)

    async def _retrieve_single_query_async(self, query: str, doc_type_filter: Optional[str] = None) -> List:
        try:
            if doc_type_filter:
                return await asyncio.to_thread(
                    self.chroma.store.similarity_search, query, k=config.RETRIEVER_K,
                    filter={"doc_type": doc_type_filter},
                )
            return await asyncio.to_thread(self.chroma.retriever.invoke, query)
        except Exception as e:
            print(f"[WARNING] Async retrieval failed for query '{query}': {e}")
            return []

    async def _retrieve_for_subqueries_async(
        self, sub_questions: List[str], doc_type_filter: Optional[str] = None
    ) -> List:
        num_subqueries = len(sub_questions)
        if not num_subqueries:
            return []

        tasks = [self._retrieve_single_query_async(sq, doc_type_filter) for sq in sub_questions]
        docs_per_question = await asyncio.gather(*tasks)

        min_per_query = config.MIN_DOCS_PER_SUBQUERY
        if min_per_query * num_subqueries > config.MAX_MULTI_STEP_DOCS:
            min_per_query = max(2, config.MAX_MULTI_STEP_DOCS // num_subqueries)

        return self._merge_retrieved(list(docs_per_question), min_per_query, num_subqueries)

    def _merge_retrieved(
        self, docs_per_question: List[List], min_per_query: int, num_subqueries: int
    ) -> List:
        all_docs: List = []
        seen_keys: set = set()
        docs_count = [0] * num_subqueries

        for idx, docs in enumerate(docs_per_question):
            for doc in docs[:min_per_query]:
                meta = doc.metadata or {}
                key = (meta.get("source", ""), meta.get("page", 0))
                if key not in seen_keys:
                    seen_keys.add(key)
                    all_docs.append(doc)
                    docs_count[idx] += 1
                    if len(all_docs) >= config.MAX_MULTI_STEP_DOCS:
                        return all_docs

        max_per = max((len(d) for d in docs_per_question), default=0)
        for i in range(min_per_query, max_per):
            for idx, docs in enumerate(docs_per_question):
                if i < len(docs):
                    doc = docs[i]
                    meta = doc.metadata or {}
                    key = (meta.get("source", ""), meta.get("page", 0))
                    if key not in seen_keys:
                        seen_keys.add(key)
                        all_docs.append(doc)
                        docs_count[idx] += 1
                        if len(all_docs) >= config.MAX_MULTI_STEP_DOCS:
                            return all_docs

        return all_docs

    # ── Follow-ups ────────────────────────────────────────────────────────────

    def _generate_followups(
        self,
        question: str,
        answer: str,
        conversation_history: List[Dict[str, str]],
    ) -> List[str]:
        history_text = "\n".join(
            f"{msg['role'].capitalize()}: {msg['content'][:300]}"
            for msg in (conversation_history or [])[-6:]
        )
        followup_prompt = (
            "Using ONLY the conversation history and the assistant's answer below,\n"
            "generate up to 5 short suggested follow-up questions the user might ask next.\n"
            "Tailor suggestions to any contextual details present in the history (major, year, courses, preferences).\n"
            "If no specific context is available, produce general useful follow-ups related to the question and answer.\n"
            "Return ONLY a valid JSON array of strings (e.g. [\"...\", \"...\"]).\n\n"
            f"CONVERSATION_HISTORY:\n{history_text}\n\n"
            f"QUESTION:\n{question}\n\n"
            f"ASSISTANT_ANSWER:\n{answer}\n\nJSON_ARRAY:"
        )
        try:
            resp = self.decompose_llm.invoke(followup_prompt)
            resp_text = resp.content.strip()
            j_start = resp_text.find("[")
            j_end = resp_text.rfind("]") + 1
            if j_start >= 0 and j_end > j_start:
                data = json.loads(resp_text[j_start:j_end])
                if isinstance(data, list):
                    return [str(s).strip() for s in data if isinstance(s, str)][:5]
        except Exception as e:
            print(f"[WARNING] Follow-up generation failed: {e}")
        return [
            "Can you clarify what you meant by that?",
            "Do you want more details about any specific course or policy mentioned?",
            "Would you like recommendations based on your major or year?",
        ]

    # ── RAG entry points ──────────────────────────────────────────────────────

    def _retrieve_docs(
        self, search_query: str, question: str, question_category: str,
        doc_type_filter: Optional[str], use_multi_step: bool
    ) -> List:
        simple = self._is_simple_query(search_query)
        if use_multi_step and not simple:
            sub_questions = self._decompose_query(search_query)
            if question_category == "course_catalog" and self._is_sequence_question(question):
                sub_questions = self._prioritize_sequence_queries(sub_questions, search_query, question, max_queries=8)
            docs = self._retrieve_for_subqueries(sub_questions, doc_type_filter)
        else:
            if doc_type_filter:
                docs = self.chroma.store.similarity_search(search_query, k=config.RETRIEVER_K, filter={"doc_type": doc_type_filter})
            else:
                docs = self.chroma.retriever.invoke(search_query)

        if question_category == "course_catalog" and self._is_sequence_question(question):
            boosted_docs = []
            for f in [{"section": "freeman_core"}, {"section": "sequence"}]:
                filt = {"$and": [{"doc_type": "catalog"}, f]}
                boosted_docs.extend(self.chroma.store.similarity_search(search_query, k=max(6, config.RETRIEVER_K // 2), filter=filt))
            if boosted_docs:
                docs = self._merge_docs(docs, boosted_docs)

        docs = self._augment_management_plan_docs(docs, question, search_query)
        docs = self._enrich_with_course_entries(docs, question)
        return docs

    async def _retrieve_docs_async(
        self, search_query: str, question: str, question_category: str,
        doc_type_filter: Optional[str], use_multi_step: bool
    ) -> List:
        simple = self._is_simple_query(search_query)
        if use_multi_step and not simple:
            sub_questions = await asyncio.to_thread(self._decompose_query, search_query)
            if question_category == "course_catalog" and self._is_sequence_question(question):
                sub_questions = self._prioritize_sequence_queries(sub_questions, search_query, question, max_queries=8)
            docs = await self._retrieve_for_subqueries_async(sub_questions, doc_type_filter)
        else:
            if doc_type_filter:
                docs = await asyncio.to_thread(self.chroma.store.similarity_search, search_query, k=config.RETRIEVER_K, filter={"doc_type": doc_type_filter})
            else:
                docs = await asyncio.to_thread(self.chroma.retriever.invoke, search_query)

        if question_category == "course_catalog" and self._is_sequence_question(question):
            boosted_docs = []
            for f in [{"section": "freeman_core"}, {"section": "sequence"}]:
                filt = {"$and": [{"doc_type": "catalog"}, f]}
                boost = await asyncio.to_thread(self.chroma.store.similarity_search, search_query, k=max(6, config.RETRIEVER_K // 2), filter=filt)
                boosted_docs.extend(boost)
            if boosted_docs:
                docs = self._merge_docs(docs, boosted_docs)

        docs = self._augment_management_plan_docs(docs, question, search_query)
        docs = self._enrich_with_course_entries(docs, question)
        return docs

    def _generate_answer(
        self, question: str, docs: List, question_category: str,
        conversation_history: List[Dict[str, str]],
        conversation_summary: Optional[str],
        user_profile: Optional[Dict[str, Any]],
    ) -> Tuple[str, List[Dict[str, Any]], List[str]]:
        """Invoke LLM, post-process answer, build citations & follow-ups. Returns (answer, citations, followups)."""
        knowledge = self._prepare_knowledge(docs)
        citations = self._build_citations(docs)

        history_context = ""
        if conversation_history:
            history_context = "\n".join(
                f"{msg['role'].capitalize()}: {msg['content'][:300]}"
                for msg in conversation_history[-6:]
            )

        user_prompt = get_user_prompt(
            question, knowledge, history_context or "",
            summary=conversation_summary or None,
            user_profile=user_profile or None,
        )
        messages = [
            SystemMessage(content=self._get_system_prompt(question_category)),
            HumanMessage(content=user_prompt),
        ]

        FALLBACK = (
            "I'm not seeing that information in the documents I have, but I'm happy to help with anything else! "
            "For official guidance and questions about how these policies apply to your specific situation, please consult with your academic advisor or the Office of the Registrar."
        )

        try:
            response = self.llm.invoke(messages)
            answer = self._normalize_text((response.content or "").strip())

            if not answer:
                answer = FALLBACK
            elif FALLBACK in answer and citations:
                if answer.strip() != FALLBACK:
                    answer = answer.replace(FALLBACK, "").strip()
                if not answer:
                    answer = FALLBACK

            if answer != FALLBACK and question_category in ("academic_policy", "course_catalog"):
                answer = answer + config.POLICY_DISCLAIMER

            followups = [] if answer == FALLBACK else self._generate_followups(question, answer, conversation_history)
            return answer, citations, followups

        except Exception as e:
            print(f"[ERROR] LLM generation error: {e}")
            return (
                "Sorry, I encountered an error generating a response. Please try again or contact your academic advisor.",
                citations,
                [],
            )

    # ── Public sync entry point ───────────────────────────────────────────────

    def get_answer(
        self,
        question: str,
        conversation_history: List[Dict[str, str]],
        use_multi_step: Optional[bool] = None,
        conversation_summary: Optional[str] = None,
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, List[Dict], str, List[str]]:
        question_category = self._classify_question(question, conversation_history)

        conv_response = self._get_llm_conversational_response(question_category, question, conversation_history)
        if conv_response is not None:
            return (conv_response, [], question_category, [])

        doc_type_filter = "catalog" if question_category == "course_catalog" else ("policy" if question_category == "academic_policy" else None)

        if use_multi_step is None:
            use_multi_step = config.USE_MULTI_STEP_QUERY

        search_query = self._build_contextual_query(question, conversation_history)

        try:
            docs = self._retrieve_docs(search_query, question, question_category, doc_type_filter, use_multi_step)
        except Exception as e:
            print(f"[ERROR] Retrieval error: {e}")
            return ("Sorry, I ran into an error retrieving information. Please try again later or contact support.", [], question_category, [])

        if not docs:
            fallback = "I'm not seeing that information in the documents I have, but I'm happy to help with anything else! For official guidance, please consult with your academic advisor or the Office of the Registrar."
            return (fallback, [], question_category, [])

        answer, citations, followups = self._generate_answer(question, docs, question_category, conversation_history, conversation_summary, user_profile)
        return (answer, citations, question_category, followups)

    def recommend_courses_from_schedule(
        self,
        schedule_summary: str,
        conversation_history: List[Dict[str, str]],
    ) -> Tuple[str, List[Dict], str]:
        question = (
            "A student shared their previously completed courses and experiences:\n"
            f"{schedule_summary}\n\n"
            "Using the Bucknell course catalog, recommend 4-6 thoughtful next courses that build on this plan. "
            "Group suggestions by category when possible (Major requirements, Core/Electives, Exploratory). "
            "Consider prerequisites and avoid recommending courses that appear to already be completed."
        )
        answer, citations, category, _ = self.get_answer(question, conversation_history)
        return answer, citations, category

    # ── Public async entry points ─────────────────────────────────────────────

    async def get_answer_async(
        self,
        question: str,
        conversation_history: List[Dict[str, str]],
        use_multi_step: Optional[bool] = None,
        conversation_summary: Optional[str] = None,
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, List[Dict], str, List[str]]:
        classify_task = asyncio.to_thread(self._classify_question, question, conversation_history)
        context_task = asyncio.to_thread(self._build_contextual_query, question, conversation_history)
        results = await asyncio.gather(classify_task, context_task, return_exceptions=True)

        question_category = results[0] if not isinstance(results[0], Exception) else "course_catalog"
        search_query = results[1] if not isinstance(results[1], Exception) else question

        conv_response = await asyncio.to_thread(self._get_llm_conversational_response, question_category, question, conversation_history)
        if conv_response is not None:
            return (conv_response, [], question_category, [])

        doc_type_filter = "catalog" if question_category == "course_catalog" else ("policy" if question_category == "academic_policy" else None)

        if use_multi_step is None:
            use_multi_step = config.USE_MULTI_STEP_QUERY

        try:
            docs = await self._retrieve_docs_async(search_query, question, question_category, doc_type_filter, use_multi_step)
        except Exception as e:
            print(f"[ERROR] Retrieval error: {e}")
            return ("Sorry, I ran into an error retrieving information. Please try again later or contact support.", [], question_category, [])

        if not docs:
            fallback = "I'm not seeing that information in the documents I have, but I'm happy to help with anything else! For official guidance, please consult with your academic advisor or the Office of the Registrar."
            return (fallback, [], question_category, [])

        knowledge = self._prepare_knowledge(docs)
        citations = self._build_citations(docs)

        history_context = "\n".join(
            f"{msg['role'].capitalize()}: {msg['content'][:300]}"
            for msg in (conversation_history or [])[-6:]
        ) if conversation_history else ""

        user_prompt = get_user_prompt(
            question, knowledge, history_context or "",
            summary=conversation_summary or None,
            user_profile=user_profile or None,
        )
        messages = [
            SystemMessage(content=self._get_system_prompt(question_category)),
            HumanMessage(content=user_prompt),
        ]

        FALLBACK = (
            "I'm not seeing that information in the documents I have, but I'm happy to help with anything else! "
            "For official guidance and questions about how these policies apply to your specific situation, please consult with your academic advisor or the Office of the Registrar."
        )

        try:
            response = await asyncio.to_thread(self.llm.invoke, messages)
            answer = self._normalize_text((response.content or "").strip())

            if not answer:
                answer = FALLBACK
            elif FALLBACK in answer and citations:
                if answer.strip() != FALLBACK:
                    answer = answer.replace(FALLBACK, "").strip()
                if not answer:
                    answer = FALLBACK

            if answer != FALLBACK and question_category == "academic_policy":
                answer = answer + config.POLICY_DISCLAIMER

            followups: List[str] = []
            if answer != FALLBACK:
                followups = await asyncio.to_thread(self._generate_followups, question, answer, conversation_history)

            return answer, citations, question_category, followups

        except Exception as e:
            print(f"[ERROR] LLM generation error: {e}")
            return ("Sorry, I encountered an error generating a response. Please try again or contact your academic advisor.", citations, question_category, [])

    async def get_answer_streaming(
        self,
        question: str,
        conversation_history: List[Dict[str, str]],
        use_multi_step: Optional[bool] = None,
        conversation_summary: Optional[str] = None,
        user_profile: Optional[Dict[str, Any]] = None,
    ):
        """Async generator that yields SSE-formatted events."""
        import json as _json

        classify_task = asyncio.to_thread(self._classify_question, question, conversation_history)
        context_task = asyncio.to_thread(self._build_contextual_query, question, conversation_history)
        results = await asyncio.gather(classify_task, context_task, return_exceptions=True)

        question_category = results[0] if not isinstance(results[0], Exception) else "course_catalog"
        search_query = results[1] if not isinstance(results[1], Exception) else question

        conv_response = await asyncio.to_thread(self._get_llm_conversational_response, question_category, question, conversation_history)
        if conv_response is not None:
            yield f"event: metadata\ndata: {_json.dumps({'category': question_category, 'citations': []})}\n\n"
            yield f"event: token\ndata: {_json.dumps({'token': conv_response})}\n\n"
            yield f"event: done\ndata: {_json.dumps({'answer': conv_response, 'citations': [], 'category': question_category})}\n\n"
            return

        doc_type_filter = "catalog" if question_category == "course_catalog" else ("policy" if question_category == "academic_policy" else None)

        if use_multi_step is None:
            use_multi_step = config.USE_MULTI_STEP_QUERY

        try:
            docs = await self._retrieve_docs_async(search_query, question, question_category, doc_type_filter, use_multi_step)
        except Exception as e:
            print(f"[ERROR] Retrieval error: {e}")
            error_msg = "Sorry, I ran into an error retrieving information. Please try again later or contact support."
            yield f"event: metadata\ndata: {_json.dumps({'category': question_category, 'citations': []})}\n\n"
            yield f"event: token\ndata: {_json.dumps({'token': error_msg})}\n\n"
            yield f"event: done\ndata: {_json.dumps({'answer': error_msg, 'citations': [], 'category': question_category})}\n\n"
            return

        if not docs:
            fallback = "I'm not seeing that information in the documents I have, but I'm happy to help with anything else! For official guidance, please consult with your academic advisor or the Office of the Registrar."
            yield f"event: metadata\ndata: {_json.dumps({'category': question_category, 'citations': []})}\n\n"
            yield f"event: token\ndata: {_json.dumps({'token': fallback})}\n\n"
            yield f"event: done\ndata: {_json.dumps({'answer': fallback, 'citations': [], 'category': question_category})}\n\n"
            return

        knowledge = self._prepare_knowledge(docs)
        citations = self._build_citations(docs)

        yield f"event: metadata\ndata: {_json.dumps({'category': question_category, 'citations': citations})}\n\n"

        history_context = "\n".join(
            f"{msg['role'].capitalize()}: {msg['content'][:300]}"
            for msg in (conversation_history or [])[-6:]
        ) if conversation_history else ""

        user_prompt = get_user_prompt(
            question, knowledge, history_context or "",
            summary=conversation_summary or None,
            user_profile=user_profile or None,
        )
        messages = [
            SystemMessage(content=self._get_system_prompt(question_category)),
            HumanMessage(content=user_prompt),
        ]

        FALLBACK = (
            "I'm not seeing that information in the documents I have, but I'm happy to help with anything else!"
            "For official guidance and questions about how these policies apply to your specific situation, "
            "please consult with your academic advisor or the Office of the Registrar."
        )

        full_answer = ""
        try:
            async for chunk in self.llm.astream(messages):
                token = chunk.content or ""
                if token:
                    full_answer += token
                    yield f"event: token\ndata: {_json.dumps({'token': token})}\n\n"
        except Exception as e:
            print(f"[ERROR] Streaming LLM error: {e}")
            if not full_answer:
                error_msg = "Sorry, I encountered an error generating a response. Please try again or contact your academic advisor."
                yield f"event: token\ndata: {_json.dumps({'token': error_msg})}\n\n"
                full_answer = error_msg

        answer = self._normalize_text(full_answer.strip())

        if answer != FALLBACK and question_category in ("academic_policy", "course_catalog"):
            yield f"event: token\ndata: {_json.dumps({'token': config.POLICY_DISCLAIMER})}\n\n"
            answer = answer + config.POLICY_DISCLAIMER

        if answer and answer != FALLBACK:
            try:
                followups = await asyncio.to_thread(self._generate_followups, question, answer, conversation_history)
                yield f"event: followups\ndata: {_json.dumps({'follow_ups': followups})}\n\n"
            except Exception as e:
                print(f"[WARNING] Follow-up generation failed: {e}")
                yield f"event: followups\ndata: {_json.dumps({'follow_ups': []})}\n\n"
        else:
            yield f"event: followups\ndata: {_json.dumps({'follow_ups': []})}\n\n"

        yield f"event: done\ndata: {_json.dumps({'answer': answer, 'citations': citations, 'category': question_category})}\n\n"
