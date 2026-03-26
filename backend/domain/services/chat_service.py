"""
Service for handling chatbot RAG (Retrieval-Augmented Generation) operations.

This module defines the ChatbotService class, which manages the interaction
between the user, the vector database (Chroma), and the LLM (OpenAI).
It handles query classification, decomposition, document retrieval,
response generation, and follow-up suggestion.
"""
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.messages import SystemMessage, HumanMessage
from typing import List, Dict, Tuple, Optional, Any
import asyncio
import os
import re
import json
import config  # backward-compat shim (for message constants)
from core.settings import settings
from prompts import get_decompose_prompt, get_user_prompt, get_contextualize_prompt, \
    get_question_classifier_prompt, get_conversational_prompt, \
    SYSTEM_PROMPT, CONVERSATIONAL_SYSTEM_PROMPT, CATALOG_SYSTEM_PROMPT, POLICY_SYSTEM_PROMPT
import math

class ChatbotService:
    """Service for handling chatbot RAG operations"""
    
    def __init__(self):
        """Initialize the chatbot service with embeddings and vector store"""
        # Initialize embeddings model
        self.embeddings_model = OpenAIEmbeddings(model=settings.llm.EMBEDDING_MODEL)
        
        # Initialize LLM with modest temperature for factual responses
        self.llm = ChatOpenAI(
            temperature=0.3,
            model=settings.llm.OPENAI_MODEL
        )
        
        # Initialize a separate LLM for query decomposition (lower temperature)
        self.decompose_llm = ChatOpenAI(
            temperature=0.1,
            model=settings.llm.OPENAI_LIGHT_MODEL
        )

        # Initialize a separate LLM for question classification (very low temperature)
        self.classifier_llm = ChatOpenAI(
            temperature=settings.rag.QUESTION_CLASSIFIER_TEMPERATURE,
            model=settings.llm.OPENAI_LIGHT_MODEL
        )

        # Connect to ChromaDB
        self.vector_store = Chroma(
            collection_name=settings.vector.CHROMA_COLLECTION_NAME,
            embedding_function=self.embeddings_model,
            persist_directory=settings.vector.CHROMA_PATH,
        )
        
        # Set up retriever with MMR for diverse but relevant chunks
        self.retriever = self.vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": settings.rag.RETRIEVER_K,
                "fetch_k": settings.rag.RETRIEVER_FETCH_K,
                "lambda_mult": settings.rag.RETRIEVER_LAMBDA_MULT
            }
        )
    
    def _short_source(self, path: str) -> str:
        """Turn a long file path into a friendly filename for citations.

        Args:
            path: The full file path.

        Returns:
            str: The friendly filename.
        """
        if not path:
            return "Source"
        name = os.path.basename(path)
        return name.replace("_", " ")

    def _classify_question(
        self, question: str, conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Classify a question as 'course_catalog', 'academic_policy', or 'off_topic'.

        This pre-retrieval classification allows us to:
        1. Reject off-topic questions immediately
        2. Filter ChromaDB searches to relevant document types

        Args:
            question: The user's question
            conversation_history: Optional prior turns for follow-up context.

        Returns:
            str: One of 'course_catalog', 'academic_policy', 'off_topic', 'greeting',
            'thank_you', or 'clarification_needed'. Falls back to 'course_catalog' on error.
        """
        if not settings.rag.ENABLE_OFF_TOPIC_DETECTION:
            return "course_catalog"

        history_text = self._format_history_context(conversation_history or [])
        classifier_prompt = get_question_classifier_prompt(question, history_text)

        try:
            response = self.classifier_llm.invoke(classifier_prompt)
            response_text = response.content.strip()

            # Extract JSON
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                data = json.loads(json_str)

                category = data.get("category", "course_catalog")

                # Validate category
                if category in ["course_catalog", "academic_policy", "off_topic", "greeting", "thank_you", "clarification_needed"]:
                    # Deterministic guard: a short follow-up in an active conversation
                    # should never be treated as clarification_needed.
                    if category == "clarification_needed" and conversation_history:
                        print(f"[CLASSIFICATION] 'clarification_needed' overridden to 'course_catalog' (active conversation)")
                        return "course_catalog"
                    print(f"[CLASSIFICATION] Question classified as: {category}")
                    return category
                else:
                    print(f"[WARNING] Invalid category '{category}', defaulting to 'course_catalog'")
                    return "course_catalog"

        except (json.JSONDecodeError, KeyError, AttributeError) as e:
            print(f"[WARNING] Question classification failed: {e}. Defaulting to 'course_catalog'")

        # Fallback to catalog (safer than rejecting)
        return "course_catalog"

    def _get_system_prompt(self, question_category: str) -> str:
        """Return the appropriate system prompt for the question category."""
        if question_category == "course_catalog":
            return CATALOG_SYSTEM_PROMPT
        if question_category == "academic_policy":
            return POLICY_SYSTEM_PROMPT
        return SYSTEM_PROMPT  # fallback for unexpected categories

    def _get_llm_conversational_response(
        self,
        category: str,
        question: str,
        conversation_history: List[Dict[str, str]],
    ) -> Optional[str]:
        """Use decompose_llm to generate a natural conversational reply.

        Handles greeting, thank_you, clarification_needed, and off_topic categories.
        Falls back to None (triggering full RAG) on unexpected errors.

        Args:
            category: The classification category of the user's input.
            question: The student's original message.
            conversation_history: The history of the conversation.

        Returns:
            Optional[str]: LLM-generated response string, or None if the category
            requires RAG.
        """
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

    def _get_document_url(self, source_filename: str, page: int, source_url: Optional[str] = None, doc_type: Optional[str] = None) -> Optional[str]:
        """Generate appropriate URL for a document citation based on its source.

        Args:
            source_filename: Base filename (e.g., "GRADE REPLACEMENT POLICY.pdf")
            page: Page number (1-indexed)
            source_url: Optional external URL (e.g., Google Docs viewer link)
            doc_type: Optional document type (e.g., "catalog", "policy")

        Returns:
            Optional[str]: URL string for the frontend to link to, or None if no link is available.
        """
        if source_url:
            return source_url
        if doc_type == "policy":
            return None

        # Catalog PDF is served as a stable public asset from the frontend.
        # Use a relative URL so it works in any environment/domain.
        return f"/catalog.pdf#page={page}"

    def _extract_course_codes(self, docs: List) -> List[str]:
        """Extract course codes from retrieved docs (e.g., CSCI 306).

        Used to enrich sequence/plan answers with full course titles.

        Args:
            docs: List of retrieved documents.

        Returns:
            List[str]: A sorted list of unique course codes found in the documents.
        """
        code_re = re.compile(r'\b[A-Z]{2,4}\s?\d{3}[A-Z]?\b')
        codes = set()
        for doc in docs:
            text = (doc.page_content or "")
            for m in code_re.finditer(text):
                code = m.group(0).upper()
                code = re.sub(r'\s+', ' ', code).strip()
                codes.add(code)
        return sorted(codes)

    def _enrich_with_course_entries(self, docs: List, question: str) -> List:
        """For sequence/plan questions, pull course-entry chunks by course code.

        This ensures titles/descriptions are available to the model.

        Args:
            docs: List of initially retrieved documents.
            question: The user's question.

        Returns:
            List: Enriched list of documents including specific course entries.
        """
        if not docs or not self._is_sequence_question(question):
            return docs

        codes = self._extract_course_codes(docs)
        if not codes:
            return docs

        # Cap to avoid over-fetching
        max_codes = 14
        extra_docs = []
        for code in codes[:max_codes]:
            # Try exact course_code metadata match (with and without space)
            variants = [code, code.replace(" ", "")]
            found = []
            for variant in variants:
                filt = {"$and": [{"doc_type": "catalog"}, {"course_code": variant}]}
                found = self.vector_store.similarity_search(code, k=1, filter=filt)
                if found:
                    break

            if not found:
                # Fallback: best-effort semantic match within catalog
                found = self.vector_store.similarity_search(code, k=2, filter={"doc_type": "catalog"})

            if found:
                extra_docs.extend(found)

        if extra_docs:
            return self._merge_docs(docs, extra_docs)
        return docs

    def _augment_management_plan_docs(self, docs: List, question: str, search_query: str) -> List:
        """Force-include Freeman/BSBA-wide requirement chunks for management plan questions.

        Semantic search often over-indexes on the major-specific suggested plan and
        under-retrieves the college-wide BSBA requirements. For full management plan
        questions, add those requirement chunks explicitly.
        """
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
            found = self.vector_store.similarity_search(
                query,
                k=2,
                filter={"doc_type": "catalog"},
            )
            if found:
                extra_docs.extend(found)

        if extra_docs:
            return self._merge_docs(docs, extra_docs)
        return docs

    def _dedupe_citations(self, citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate citations while preserving order.

        Args:
            citations: List of citation dictionaries.

        Returns:
            List[Dict[str, Any]]: Deduplicated list of citations.
        """
        seen = set()
        deduped: List[Dict[str, Any]] = []
        for c in citations:
            key = (
                c.get("source"),
                c.get("page"),
                c.get("content"),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(c)
        return deduped

    def _prepare_knowledge(self, docs) -> str:
        """Build a labeled context string so the model can cite pages.

        Each chunk gets headers before and after for better citation tracking.

        Args:
            docs: List of documents to format.

        Returns:
            str: The formatted context string.
        """
        parts = []
        for d in docs:
            meta = d.metadata or {}
            src = self._short_source(meta.get("source", "Catalogue"))
            # PyPDFDirectoryLoader is 0-based; add 1 for human-friendly
            page = (meta.get("page", 0) or 0) + 1
            header = f"[{src}, p. {page}]"
            # Add header before and after for better citation tracking
            content = self._normalize_text(d.page_content).strip()
            parts.append(f"{header}\n{content}\n{header}\n")
        return "\n".join(parts)

    def _normalize_text(self, text: str) -> str:
        """Normalize spacing artifacts from PDF extraction and model output.

        Removes spaces before common punctuation.

        Args:
            text: The text to normalize.

        Returns:
            str: The normalized text.
        """
        if not text:
            return text
        return re.sub(r"\s+([,.;:!?])", r"\1", text)
    
    def _decompose_query(self, question: str) -> List[str]:
        """Decompose a complex query into multiple sub-questions using structured JSON output.
        
        This helps with comparison queries, multi-part questions, and complex reasoning.
        
        Args:
            question: The original user question.
            
        Returns:
            List[str]: List of sub-questions (or single question if decomposition not needed).
        """
        decompose_prompt = get_decompose_prompt(question)

        try:
            response = self.decompose_llm.invoke(decompose_prompt)
            response_text = response.content.strip()
            
            # Try to extract JSON even if there's extra text
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                data = json.loads(json_str)
                
                # Handle different response types
                if data.get("type") == "simple" or not data.get("sub_questions"):
                    return [question]
                
                if data.get("type") == "too_broad":
                    # Return original question but log warning
                    suggestion = data.get("suggestion", "Please narrow your question.")
                    print(f"[WARNING] Query too broad. Suggestion: {suggestion}")
                    return [question]  # Fallback to single retrieval
                
                sub_questions = data.get("sub_questions", [])
                if isinstance(sub_questions, list) and sub_questions:
                    # Enforce maximum limit
                    if len(sub_questions) > 5:
                        print(f"[WARNING] Too many sub-questions ({len(sub_questions)}). Limiting to first 5.")
                        sub_questions = sub_questions[:5]
                    return sub_questions
            
        except (json.JSONDecodeError, KeyError, AttributeError) as e:
            # Fallback: if JSON parsing fails, use original question
            print(f"[WARNING] Query decomposition failed: {e}. Using original question.")
        
        # Fallback to original question
        return [question]
    
    def _retrieve_for_subqueries(self, sub_questions: List[str], doc_type_filter: Optional[str] = None) -> List:
        """Retrieve documents for multiple sub-questions with adaptive allocation.

        Strategy:
        1. Guarantee minimum documents per sub-question
        2. Distribute remaining budget proportionally
        3. Use round-robin for balanced representation

        Args:
            sub_questions: List of sub-questions to retrieve for.
            doc_type_filter: Optional document type to filter by ('catalog' or 'policy').

        Returns:
            List: Combined list of unique documents.
        """
        num_subqueries = len(sub_questions)
        if num_subqueries == 0:
            return []
        
        # Calculate adaptive retrieval limits
        min_per_query = settings.rag.MIN_DOCS_PER_SUBQUERY
        total_min = min_per_query * num_subqueries
        
        # Adjust strategy based on number of sub-questions
        if total_min > settings.rag.MAX_MULTI_STEP_DOCS:
            # Too many sub-questions - reduce minimum guarantee
            min_per_query = max(2, settings.rag.MAX_MULTI_STEP_DOCS // num_subqueries)
            print(f"[INFO] Many sub-questions ({num_subqueries}). Adjusting to {min_per_query} docs minimum per query.")
        
        # Retrieve documents for each sub-question
        docs_per_question = []
        for sub_q in sub_questions:
            try:
                # Apply doc_type filter if specified
                if doc_type_filter:
                    docs = self.vector_store.similarity_search(
                        sub_q,
                        k=settings.rag.RETRIEVER_K,
                        filter={"doc_type": doc_type_filter}
                    )
                else:
                    docs = self.retriever.invoke(sub_q)
                docs_per_question.append(docs)
            except Exception as e:
                print(f"[WARNING] Retrieval failed for sub-query '{sub_q}': {e}")
                docs_per_question.append([])
        
        # Phase 1: Guarantee minimum documents per sub-question
        all_docs = []
        seen_keys = set()
        docs_count_per_query = [0] * num_subqueries
        
        for idx, docs in enumerate(docs_per_question):
            for doc in docs[:min_per_query]:  # Take up to minimum
                meta = doc.metadata or {}
                key = (meta.get("source", ""), meta.get("page", 0))
                if key not in seen_keys:
                    seen_keys.add(key)
                    all_docs.append(doc)
                    docs_count_per_query[idx] += 1
                    
                    if len(all_docs) >= settings.rag.MAX_MULTI_STEP_DOCS:
                        return all_docs
        
        # Phase 2: Round-robin for remaining slots
        max_per_question = max(len(docs) for docs in docs_per_question) if docs_per_question else 0
        
        for i in range(min_per_query, max_per_question):
            for idx, docs in enumerate(docs_per_question):
                if i < len(docs):
                    doc = docs[i]
                    meta = doc.metadata or {}
                    key = (meta.get("source", ""), meta.get("page", 0))
                    if key not in seen_keys:
                        seen_keys.add(key)
                        all_docs.append(doc)
                        docs_count_per_query[idx] += 1
                        
                        if len(all_docs) >= settings.rag.MAX_MULTI_STEP_DOCS:
                            # Log distribution for debugging
                            print(f"[INFO] Document distribution: {dict(zip(range(1, num_subqueries+1), docs_count_per_query))}")
                            return all_docs
        
        print(f"[INFO] Final document distribution: {dict(zip(range(1, num_subqueries+1), docs_count_per_query))}")
        return all_docs

    async def _retrieve_single_query_async(self, query: str, doc_type_filter: Optional[str] = None) -> List:
        """Run a single retrieval call in a thread for async usage.

        Args:
            query: The search query.
            doc_type_filter: Optional document type filter.

        Returns:
            List: A list of retrieved documents.
        """
        try:
            if doc_type_filter:
                return await asyncio.to_thread(
                    self.vector_store.similarity_search,
                    query, k=settings.rag.RETRIEVER_K,
                    filter={"doc_type": doc_type_filter}
                )
            else:
                return await asyncio.to_thread(self.retriever.invoke, query)
        except Exception as e:
            print(f"[WARNING] Async retrieval failed for query '{query}': {e}")
            return []

    async def _retrieve_for_subqueries_async(self, sub_questions: List[str], doc_type_filter: Optional[str] = None) -> List:
        """Async version of _retrieve_for_subqueries.
        
        Fires all sub-question retrievals in parallel, then applies the same Phase 1 + Phase 2 merge logic.

        Args:
            sub_questions: List of sub-questions.
            doc_type_filter: Optional document type filter.

        Returns:
            List: Combined list of unique documents.
        """
        num_subqueries = len(sub_questions)
        if num_subqueries == 0:
            return []

        # Fire all retrievals in parallel
        tasks = [self._retrieve_single_query_async(sq, doc_type_filter) for sq in sub_questions]
        docs_per_question = await asyncio.gather(*tasks)

        # Calculate adaptive retrieval limits
        min_per_query = settings.rag.MIN_DOCS_PER_SUBQUERY
        total_min = min_per_query * num_subqueries

        if total_min > settings.rag.MAX_MULTI_STEP_DOCS:
            min_per_query = max(2, settings.rag.MAX_MULTI_STEP_DOCS // num_subqueries)
            print(f"[INFO] Many sub-questions ({num_subqueries}). Adjusting to {min_per_query} docs minimum per query.")

        # Phase 1: Guarantee minimum documents per sub-question
        all_docs = []
        seen_keys = set()
        docs_count_per_query = [0] * num_subqueries

        for idx, docs in enumerate(docs_per_question):
            for doc in docs[:min_per_query]:
                meta = doc.metadata or {}
                key = (meta.get("source", ""), meta.get("page", 0))
                if key not in seen_keys:
                    seen_keys.add(key)
                    all_docs.append(doc)
                    docs_count_per_query[idx] += 1
                    if len(all_docs) >= settings.rag.MAX_MULTI_STEP_DOCS:
                        return all_docs

        # Phase 2: Round-robin for remaining slots
        max_per_question = max(len(docs) for docs in docs_per_question) if docs_per_question else 0

        for i in range(min_per_query, max_per_question):
            for idx, docs in enumerate(docs_per_question):
                if i < len(docs):
                    doc = docs[i]
                    meta = doc.metadata or {}
                    key = (meta.get("source", ""), meta.get("page", 0))
                    if key not in seen_keys:
                        seen_keys.add(key)
                        all_docs.append(doc)
                        docs_count_per_query[idx] += 1
                        if len(all_docs) >= settings.rag.MAX_MULTI_STEP_DOCS:
                            print(f"[INFO] Document distribution: {dict(zip(range(1, num_subqueries+1), docs_count_per_query))}")
                            return all_docs

        print(f"[INFO] Final document distribution: {dict(zip(range(1, num_subqueries+1), docs_count_per_query))}")
        return all_docs

    def _merge_docs(self, base_docs: List, extra_docs: List) -> List:
        """Merge document lists, de-duplicating by (source, page).

        Args:
            base_docs: The primary list of documents.
            extra_docs: The list of documents to add.

        Returns:
            List: The merged list of documents.
        """
        merged = list(base_docs)
        seen = set()
        for d in merged:
            meta = d.metadata or {}
            seen.add((meta.get("source", ""), meta.get("page", 0)))
        for d in extra_docs:
            meta = d.metadata or {}
            key = (meta.get("source", ""), meta.get("page", 0))
            if key not in seen:
                seen.add(key)
                merged.append(d)
        return merged
    
    def _build_contextual_query(self, question: str, conversation_history: List[Dict[str, str]]) -> str:
        """Build a contextual query that incorporates conversation history for better follow-up handling.
        
        Args:
            question: Current user question.
            conversation_history: Previous conversation turns.
            
        Returns:
            str: Standalone query that includes necessary context.
        """
        if not conversation_history:
            return question
        
        # Only use last 2-3 exchanges (4-6 messages) for context
        recent_history = conversation_history[-6:]
        if not recent_history:
            return question
        
        # Format history concisely
        history_text = "\n".join([
            f"{msg['role'].capitalize()}: {msg['content'][:150]}"  # Truncate long messages
            for msg in recent_history
        ])
        
        contextualize_prompt = get_contextualize_prompt(question, history_text)
        
        try:
            response = self.decompose_llm.invoke(contextualize_prompt)
            contextual_query = response.content.strip()
            
            # Validate that we got a reasonable response
            if contextual_query and len(contextual_query) > 10:
                return contextual_query
        except Exception as e:
            print(f"[WARNING] Contextualization failed: {e}. Using original question.")
        
        return question

    def _is_simple_query(self, question: str) -> bool:
        """Heuristic check to determine if a query is simple enough to skip decomposition.

        Simple queries are short, single-topic questions without multi-part markers.

        Args:
            question: The query to check.

        Returns:
            bool: True if the query is simple, False otherwise.
        """
        words = question.split()
        if len(words) > settings.rag.SIMPLE_QUERY_MAX_WORDS:
            return False

        q_lower = question.lower()

        # Multi-part markers indicate complex queries
        multi_part_markers = [
            " and ", " vs ", " versus ", "compare", "difference between",
            "both", "each", "as well as",
        ]
        if any(marker in q_lower for marker in multi_part_markers):
            return False

        # Multiple question marks suggest multiple questions
        if question.count("?") > 1:
            return False

        # Multiple course codes suggest a comparison
        course_codes = re.findall(r"[A-Z]{3,4}\s*\d{3}", question)
        if len(course_codes) > 1:
            return False

        # Listing patterns indicate multi-part questions
        listing_patterns = [r"\b\d+\.", r"\bfirst\b", r"\bsecond\b", r"\bthird\b"]
        if any(re.search(pat, q_lower) for pat in listing_patterns):
            return False

        return True

    def _is_sequence_question(self, question: str) -> bool:
        """Heuristic check for questions asking about a major/course sequence or plan.

        Args:
            question: The user's question.

        Returns:
            bool: True if it appears to be a sequence question.
        """
        q = question.lower()

        # Direct sequence/plan language.
        direct_markers = (
            "sequence",
            "four-year",
            "four year",
            "plan",
            "recommended sequence",
            "curriculum",
            "roadmap",
        )
        if any(key in q for key in direct_markers):
            return True

        # Schedule-by-year phrasing should also trigger sequence enrichment.
        year_markers = ("first year", "sophomore", "junior", "senior")
        schedule_markers = ("schedule", "semester", "fall", "spring", "what should i take")
        return any(y in q for y in year_markers) and any(s in q for s in schedule_markers)

    def _is_management_major_query(self, text: str) -> bool:
        """Detect Freeman College / BSBA major references in the query text."""
        q = text.lower()
        management_markers = (
            "freeman",
            "management college",
            "college of management",
            "bsba",
            "business analytics", "anop",
            "accounting",
            "finance",
            "acfm",
            "mors", "mgmt",
            "management and organizations",
            "markets, innovation & design", "mide",
            "markets innovation and design",
        )
        return any(marker in q for marker in management_markers)

    def _expand_sequence_queries(self, base_query: str, question: str) -> List[str]:
        """Expand sequence-style questions with related retrieval queries.

        Keeps expansions short and catalog-focused to avoid off-topic noise.

        Args:
            base_query: The base search query.
            question: The original user question.

        Returns:
            List[str]: A list of expanded queries.
        """
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

        # De-duplicate while preserving order
        seen = set()
        deduped = []
        for q in expansions:
            if q not in seen:
                seen.add(q)
                deduped.append(q)
        return deduped

    def _prioritize_sequence_queries(
        self,
        sub_questions: List[str],
        search_query: str,
        question: str,
        max_queries: int = 8,
    ) -> List[str]:
        """Keep sequence-specific retrieval queries from being truncated away.

        For plan questions, the sequence expansions are often more important than
        generic decomposed sub-questions. Put them first, then append any remaining
        sub-questions, de-duplicated and capped.
        """
        prioritized = self._expand_sequence_queries(search_query, question) + sub_questions
        seen = set()
        ordered: List[str] = []
        for query in prioritized:
            if query not in seen:
                seen.add(query)
                ordered.append(query)
            if len(ordered) >= max_queries:
                break
        return ordered

    async def _summarize_conversation(
        self,
        session_id: str,
        existing_summary: Optional[str],
        messages_to_summarize: List[Dict[str, str]],
    ) -> str:
        """Compress older messages into a brief summary paragraph.

        Args:
            session_id: Used only for logging.
            existing_summary: Any previous summary to incorporate.
            messages_to_summarize: Older messages no longer in the verbatim window.

        Returns:
            str: Updated summary paragraph, or existing_summary unchanged on failure.
        """
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
        """Extract and merge persistent user facts from a single message.

        Args:
            user_message: The latest user message to scan.
            existing_facts: Facts already stored for this user.

        Returns:
            Dict: Merged facts dict; unchanged on failure.
        """
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
            # Extract JSON object from any surrounding text
            json_start = raw.find('{')
            json_end = raw.rfind('}') + 1
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
                    merged[list_key] = ", ".join(sorted(
                        {c.strip().upper() for c in str(old_val).split(",")} |
                        {c.strip().upper() for c in str(new_val).split(",")}
                    ))

            print(f"[MEMORY] User facts updated: {list(merged.keys())}")
            return merged

        except (json.JSONDecodeError, Exception) as e:
            print(f"[WARNING] User fact extraction failed: {e}")
            return existing_facts

    def _generate_followups(self, question: str, answer: str, conversation_history: List[Dict[str, str]]) -> List[str]:
        """Generate up to 5 suggested follow-up questions tailored to the user's context.

        Args:
            question: The user's question.
            answer: The assistant's generated answer.
            conversation_history: The history of the conversation.

        Returns:
            List[str]: A list of suggestion strings.
        """
        # Build a concise history string for the prompt
        history_text = "\n".join([
            f"{msg['role'].capitalize()}: {msg['content'][:300]}"
            for msg in (conversation_history or [])[-6:]
        ])

        # Prompt the LLM to return a JSON array of suggestion strings
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

            # Extract JSON array from any surrounding text
            json_start = resp_text.find('[')
            json_end = resp_text.rfind(']') + 1
            if json_start >= 0 and json_end > json_start:
                arr_str = resp_text[json_start:json_end]
                data = json.loads(arr_str)
                if isinstance(data, list):
                    # Clean and limit to 5
                    suggestions = [str(s).strip() for s in data if isinstance(s, (str,))]
                    if len(suggestions) > 5:
                        suggestions = suggestions[:5]
                    return suggestions
        except Exception as e:
            print(f"[WARNING] Follow-up generation failed: {e}")

        # Fallback: simple heuristic suggestions
        fallback = [
            "Can you clarify what you meant by that?",
            "Do you want more details about any specific course or policy mentioned?",
            "Would you like recommendations based on your major or year?"
        ]
        return fallback[:3]
    
    def get_answer(
        self,
        question: str,
        conversation_history: List[Dict[str, str]],
        use_multi_step: Optional[bool] = None,
        conversation_summary: Optional[str] = None,
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, List[Dict], str, List[str]]:
        """Get an answer to a question using RAG with optional multi-step query decomposition.

        Now includes question classification and document type filtering.

        Args:
            question: The user's question.
            conversation_history: List of previous messages with 'role' and 'content'.
            use_multi_step: Whether to use multi-step query decomposition (default: from config).
            conversation_summary: Optional paragraph summarising older messages outside window.
            user_profile: Optional persistent facts about the user (major, year, etc.).

        Returns:
            Tuple[str, List[Dict], str, List[str]]: A tuple containing:
                - answer (str): The generated answer.
                - citations (List[Dict]): List of citations.
                - question_category (str): The classification of the question.
                - followups (List[str]): List of follow-up questions.
        """
        # STEP 1: Classify the question
        question_category = self._classify_question(question, conversation_history)

        # STEP 2: Handle conversational responses (greeting, thanks, clarification, off_topic)
        conv_response = self._get_llm_conversational_response(question_category, question, conversation_history)
        if conv_response is not None:
            print(f"[{question_category.upper()}] {question}")
            return (conv_response, [], question_category, [])

        # STEP 3: Determine document type filter
        doc_type_filter = None
        if question_category == "course_catalog":
            doc_type_filter = "catalog"
        elif question_category == "academic_policy":
            doc_type_filter = "policy"

        print(f"[INFO] Filtering retrieval to doc_type: {doc_type_filter}")

        try:
            # Use config default if not specified
            if use_multi_step is None:
                use_multi_step = settings.rag.USE_MULTI_STEP_QUERY

            # Build contextual query for better follow-up handling
            search_query = self._build_contextual_query(question, conversation_history)
            print(f"[INFO] Retrieval start | category={question_category} | multi_step={use_multi_step}")
            print(f"[INFO] Search query: {search_query}")

            # STEP 4: Decompose query if needed and enabled
            simple = self._is_simple_query(search_query)
            if simple:
                print(f"[INFO] Simple query detected, skipping decomposition")

            if use_multi_step and not simple:
                sub_questions = self._decompose_query(search_query)
                print(f"[INFO] Sub-questions: {len(sub_questions)}")

                # Log decomposition for debugging
                if len(sub_questions) > 1:
                    print(f"\n[DECOMPOSITION] Query Decomposition:")
                    print(f"Original: {question}")
                    print(f"Contextualized: {search_query}")
                    print(f"Number of sub-questions: {len(sub_questions)}")
                    for i, sq in enumerate(sub_questions, 1):
                        print(f"  {i}. {sq}")

                    # Warn if approaching limits
                    if len(sub_questions) >= 4:
                        print(f"[WARNING] High number of sub-questions ({len(sub_questions)}). Results may be limited per topic.")

                # Expand sequence questions for broader recall
                if question_category == "course_catalog" and self._is_sequence_question(question):
                    sub_questions = self._prioritize_sequence_queries(
                        sub_questions, search_query, question, max_queries=8
                    )

                # Retrieve documents for all sub-questions WITH FILTERING
                docs = self._retrieve_for_subqueries(sub_questions, doc_type_filter)
            else:
                # Single-step retrieval WITH FILTERING
                if doc_type_filter:
                    docs = self.vector_store.similarity_search(
                        search_query,
                        k=settings.rag.RETRIEVER_K,
                        filter={"doc_type": doc_type_filter}
                    )
                else:
                    docs = self.retriever.invoke(search_query)
            print(f"[INFO] Retrieved docs: {len(docs)}")

            # Sequence questions: boost likely sections (core curriculum / sequence guidance)
            if question_category == "course_catalog" and self._is_sequence_question(question):
                section_filters = [
                    {"section": "freeman_core"},
                    {"section": "sequence"},
                ]
                boosted_docs = []
                for f in section_filters:
                    filt = {"$and": [{"doc_type": "catalog"}, f]}
                    boosted_docs.extend(
                        self.vector_store.similarity_search(
                            search_query,
                            k=max(6, settings.rag.RETRIEVER_K // 2),
                            filter=filt
                        )
                    )
                if boosted_docs:
                    docs = self._merge_docs(docs, boosted_docs)
                    print(f"[INFO] Boosted docs added: {len(boosted_docs)}")
                    print(f"[INFO] Retrieved docs (after boost): {len(docs)}")

            docs = self._augment_management_plan_docs(docs, question, search_query)

            # Enrich sequence questions with course-entry chunks (titles/descriptions)
            docs = self._enrich_with_course_entries(docs, question)

            # Handle no results
            if not docs:
                fallback_message = (
                    "I’m not seeing that information in the documents I have, but I’m happy to help with anything else! "
                    "For official guidance and questions about how these policies apply to your specific situation, please consult with your academic advisor or the Office of the Registrar."
                )
                return (
                    fallback_message,
                    [],
                    question_category,
                    []
                )
        except Exception as e:
            print(f"[ERROR] Retrieval error: {e}")
            return (
                "Sorry, I ran into an error retrieving information. "
                "Please try again later or contact support.",
                [],
                question_category,
                []
            )

        # Build knowledge base with page citations
        knowledge = self._prepare_knowledge(docs)
        print(f"[INFO] Knowledge length: {len(knowledge)}")

        # Build citations list for API response
        citations = []
        for doc in docs:
            meta = doc.metadata or {}
            src = self._short_source(meta.get("source", "Catalogue"))
            # PyPDFDirectoryLoader is 0-based; add 1 for human-friendly
            page = (meta.get("page", 0) or 0) + 1
            source_filename = os.path.basename(meta.get("source", "catalog.pdf"))
            doc_type = meta.get("doc_type", "catalog")
            source_url = meta.get("source_url")

            # Skip policy citations that do not have a Google Docs URL
            if doc_type == "policy" and not source_url:
                continue

            citation = {
                "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                "source": src,
                "page": page,
                "url": self._get_document_url(source_filename, page, source_url, doc_type),
                "doc_type": doc_type,  # Include for frontend filtering/display
                # Preserve the raw filename so the frontend can link to local PDFs when
                # no explicit `source_url` is available.
                "filename": source_filename
            }
            citations.append(citation)
        citations = self._dedupe_citations(citations)

        # Format conversation history for context
        history_context = ""
        if conversation_history:
            history_context = "\n".join([
                f"{msg['role'].capitalize()}: {msg['content'][:300]}"  # Truncate long messages
                for msg in conversation_history[-6:]  # Last 3 exchanges
            ])

        # Build prompt using system/user message separation
        user_prompt = get_user_prompt(
            question, knowledge, history_context if conversation_history else "",
            summary=conversation_summary or None,
            user_profile=user_profile or None,
        )

        try:
            # Use system/user message structure
            messages = [
                SystemMessage(content=self._get_system_prompt(question_category)),
                HumanMessage(content=user_prompt)
            ]

            response = self.llm.invoke(messages)
            answer = self._normalize_text((response.content or "").strip())

            # If the model appended the generic fallback sentence but we have citations,
            # remove the fallback to avoid redundant/contradictory text. The fallback
            # is required when KNOWLEDGE lacks the requested info, but we already
            # retrieved citations for this answer.
            fallback_sentence = (
                "I’m not seeing that information in the documents I have, but I’m happy to help with anything else!"
                "For official guidance and questions about how these policies apply to your specific situation, please consult with your academic advisor or the Office of the Registrar.")
            if not answer:
                answer = fallback_sentence
            elif fallback_sentence in answer and citations and len(citations) > 0:
                if answer.strip() != fallback_sentence:
                    answer = answer.replace(fallback_sentence, '').strip()
                if not answer:
                    answer = fallback_sentence

            # Add disclaimer for catalog and policy responses
            if answer != fallback_sentence and question_category in ("academic_policy", "course_catalog"):
                answer = answer + config.POLICY_DISCLAIMER

            # Generate follow-up suggestions tailored to the user's context
            followups = [] if answer == fallback_sentence else self._generate_followups(question, answer, conversation_history)

            return answer, citations, question_category, followups  # type: ignore

        except Exception as e:
            print(f"[ERROR] LLM generation error: {e}")
            return (
                "Sorry, I encountered an error generating a response. "
                "Please try again or contact your academic advisor.",
                citations,
                question_category,
                []
            )

    def recommend_courses_from_schedule(self, schedule_summary: str, conversation_history: List[Dict[str, str]]) -> Tuple[str, List[Dict], str]:
        """Provide course recommendations using a student's prior schedule summary.

        Args:
            schedule_summary: A summary of the student's schedule.
            conversation_history: The history of the conversation.

        Returns:
            Tuple[str, List[Dict], str]: A tuple of (answer, citations, question_category).
        """
        question = (
            "A student shared their previously completed courses and experiences:\n"
            f"{schedule_summary}\n\n"
            "Using the Bucknell course catalog, recommend 4-6 thoughtful next courses that build on this plan. "
            "Group suggestions by category when possible (Major requirements, Core/Electives, Exploratory). "
            "Consider prerequisites and avoid recommending courses that appear to already be completed."
        )
        return self.get_answer(question, conversation_history)

    async def get_answer_async(
        self,
        question: str,
        conversation_history: List[Dict[str, str]],
        use_multi_step: Optional[bool] = None,
        conversation_summary: Optional[str] = None,
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, List[Dict], str, List[str]]:
        """Async version of get_answer that parallelizes classification and contextualization.

        Args:
            question: The user's question.
            conversation_history: List of previous messages.
            use_multi_step: Whether to use multi-step query decomposition.
            conversation_summary: Optional paragraph summarising older messages outside window.
            user_profile: Optional persistent facts about the user (major, year, etc.).

        Returns:
            Tuple[str, List[Dict], str, List[str]]: (answer, citations, question_category, followups).
        """
        # STEP 1 & 2: Run classification and contextualization in parallel
        classify_task = asyncio.to_thread(self._classify_question, question, conversation_history)
        context_task = asyncio.to_thread(self._build_contextual_query, question, conversation_history)

        results = await asyncio.gather(classify_task, context_task, return_exceptions=True)

        # Handle classification result
        if isinstance(results[0], Exception):
            print(f"[WARNING] Async classification failed: {results[0]}. Defaulting to 'course_catalog'")
            question_category = "course_catalog"
        else:
            question_category = results[0]

        # Handle contextualization result
        if isinstance(results[1], Exception):
            print(f"[WARNING] Async contextualization failed: {results[1]}. Using original question.")
            search_query = question
        else:
            search_query = results[1]

        # Handle conversational responses (greeting, thanks, clarification, off_topic)
        conv_response = await asyncio.to_thread(
            self._get_llm_conversational_response, question_category, question, conversation_history
        )
        if conv_response is not None:
            print(f"[{question_category.upper()}] {question}")
            return (conv_response, [], question_category, [])

        # Determine document type filter
        doc_type_filter = None
        if question_category == "course_catalog":
            doc_type_filter = "catalog"
        elif question_category == "academic_policy":
            doc_type_filter = "policy"

        print(f"[INFO] Filtering retrieval to doc_type: {doc_type_filter}")

        try:
            if use_multi_step is None:
                use_multi_step = settings.rag.USE_MULTI_STEP_QUERY

            print(f"[INFO] Retrieval start | category={question_category} | multi_step={use_multi_step}")
            print(f"[INFO] Search query: {search_query}")

            # STEP 3: Decompose query if needed
            simple = self._is_simple_query(search_query)
            if simple:
                print(f"[INFO] Simple query detected, skipping decomposition")

            if use_multi_step and not simple:
                sub_questions = await asyncio.to_thread(self._decompose_query, search_query)
                print(f"[INFO] Sub-questions: {len(sub_questions)}")

                if len(sub_questions) > 1:
                    print(f"\n[DECOMPOSITION] Query Decomposition:")
                    print(f"Original: {question}")
                    print(f"Contextualized: {search_query}")
                    print(f"Number of sub-questions: {len(sub_questions)}")
                    for i, sq in enumerate(sub_questions, 1):
                        print(f"  {i}. {sq}")
                    if len(sub_questions) >= 4:
                        print(f"[WARNING] High number of sub-questions ({len(sub_questions)}). Results may be limited per topic.")

                # Expand sequence questions
                if question_category == "course_catalog" and self._is_sequence_question(question):
                    sub_questions = self._prioritize_sequence_queries(
                        sub_questions, search_query, question, max_queries=8
                    )

                # STEP 4: Parallel retrieval
                docs = await self._retrieve_for_subqueries_async(sub_questions, doc_type_filter)
            else:
                # Single-step retrieval
                if doc_type_filter:
                    docs = await asyncio.to_thread(
                        self.vector_store.similarity_search,
                        search_query, k=settings.rag.RETRIEVER_K,
                        filter={"doc_type": doc_type_filter}
                    )
                else:
                    docs = await asyncio.to_thread(self.retriever.invoke, search_query)

            print(f"[INFO] Retrieved docs: {len(docs)}")

            # Sequence questions: boost likely sections
            if question_category == "course_catalog" and self._is_sequence_question(question):
                section_filters = [
                    {"section": "freeman_core"},
                    {"section": "sequence"},
                ]
                boosted_docs = []
                for f in section_filters:
                    filt = {"$and": [{"doc_type": "catalog"}, f]}
                    boost = await asyncio.to_thread(
                        self.vector_store.similarity_search,
                        search_query, k=max(6, settings.rag.RETRIEVER_K // 2),
                        filter=filt
                    )
                    boosted_docs.extend(boost)
                if boosted_docs:
                    docs = self._merge_docs(docs, boosted_docs)
                    print(f"[INFO] Boosted docs added: {len(boosted_docs)}")
                    print(f"[INFO] Retrieved docs (after boost): {len(docs)}")

            docs = self._augment_management_plan_docs(docs, question, search_query)

            # Enrich sequence questions with course-entry chunks (titles/descriptions)
            docs = self._enrich_with_course_entries(docs, question)

            if not docs:
                fallback_message = (
                    "I'm not seeing that information in the documents I have, but I'm happy to help with anything else! "
                    "For official guidance and questions about how these policies apply to your specific situation, please consult with your academic advisor or the Office of the Registrar."
                )
                return (fallback_message, [], question_category, [])

        except Exception as e:
            print(f"[ERROR] Retrieval error: {e}")
            return (
                "Sorry, I ran into an error retrieving information. Please try again later or contact support.",
                [], question_category, []
            )

        # Build knowledge and citations
        knowledge = self._prepare_knowledge(docs)
        print(f"[INFO] Knowledge length: {len(knowledge)}")

        citations = []
        for doc in docs:
            meta = doc.metadata or {}
            src = self._short_source(meta.get("source", "Catalogue"))
            page = (meta.get("page", 0) or 0) + 1
            source_filename = os.path.basename(meta.get("source", "catalog.pdf"))
            doc_type = meta.get("doc_type", "catalog")
            citation = {
                "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                "source": src,
                "page": page,
                "url": self._get_document_url(source_filename, page, meta.get("source_url")),
                "doc_type": doc_type,
            }
            citations.append(citation)
        citations = self._dedupe_citations(citations)

        # Format conversation history
        history_context = ""
        if conversation_history:
            history_context = "\n".join([
                f"{msg['role'].capitalize()}: {msg['content'][:300]}"
                for msg in conversation_history[-6:]
            ])

        user_prompt = get_user_prompt(
            question, knowledge, history_context if conversation_history else "",
            summary=conversation_summary or None,
            user_profile=user_profile or None,
        )

        try:
            messages = [
                SystemMessage(content=self._get_system_prompt(question_category)),
                HumanMessage(content=user_prompt)
            ]
            response = await asyncio.to_thread(self.llm.invoke, messages)
            answer = self._normalize_text((response.content or "").strip())

            fallback_sentence = (
                "I'm not seeing that information in the documents I have, but I'm happy to help with anything else!"
                "For official guidance and questions about how these policies apply to your specific situation, please consult with your academic advisor or the Office of the Registrar.")
            if not answer:
                answer = fallback_sentence
            elif fallback_sentence in answer and citations and len(citations) > 0:
                if answer.strip() != fallback_sentence:
                    answer = answer.replace(fallback_sentence, '').strip()
                if not answer:
                    answer = fallback_sentence

            if answer != fallback_sentence and question_category == "academic_policy":
                answer = answer + config.POLICY_DISCLAIMER

            # Generate follow-ups off the critical path (via thread)
            if answer == fallback_sentence:
                followups: List[str] = []
            else:
                followups = await asyncio.to_thread(self._generate_followups, question, answer, conversation_history)

            return answer, citations, question_category, followups  # type: ignore

        except Exception as e:
            print(f"[ERROR] LLM generation error: {e}")
            return (
                "Sorry, I encountered an error generating a response. "
                "Please try again or contact your academic advisor.",
                citations, question_category, []
            )

    async def get_answer_streaming(
        self,
        question: str,
        conversation_history: List[Dict[str, str]],
        use_multi_step: Optional[bool] = None,
        conversation_summary: Optional[str] = None,
        user_profile: Optional[Dict[str, Any]] = None,
    ):
        """Async generator that yields SSE-formatted events for streaming responses.

        Events: metadata, token, followups, done

        Args:
            question: The user's question.
            conversation_history: List of previous messages.
            use_multi_step: Whether to use multi-step query decomposition.
            conversation_summary: Optional paragraph summarising older messages outside window.
            user_profile: Optional persistent facts about the user (major, year, etc.).

        Yields:
            str: SSE-formatted event strings.
        """
        import json as _json

        # STEP 1: Parallel classification + contextualization
        classify_task = asyncio.to_thread(self._classify_question, question, conversation_history)
        context_task = asyncio.to_thread(self._build_contextual_query, question, conversation_history)
        results = await asyncio.gather(classify_task, context_task, return_exceptions=True)

        question_category = results[0] if not isinstance(results[0], Exception) else "course_catalog"
        search_query = results[1] if not isinstance(results[1], Exception) else question

        if isinstance(results[0], Exception):
            print(f"[WARNING] Async classification failed: {results[0]}")
        if isinstance(results[1], Exception):
            print(f"[WARNING] Async contextualization failed: {results[1]}")

        # Conversational responses (greeting, thanks, clarification, off_topic)
        conv_response = await asyncio.to_thread(
            self._get_llm_conversational_response, question_category, question, conversation_history
        )
        if conv_response is not None:
            print(f"[{question_category.upper()}] {question}")
            yield f"event: metadata\ndata: {_json.dumps({'category': question_category, 'citations': []})}\n\n"
            yield f"event: token\ndata: {_json.dumps({'token': conv_response})}\n\n"
            yield f"event: done\ndata: {_json.dumps({'answer': conv_response, 'citations': [], 'category': question_category})}\n\n"
            return

        doc_type_filter = None
        if question_category == "course_catalog":
            doc_type_filter = "catalog"
        elif question_category == "academic_policy":
            doc_type_filter = "policy"

        # STEP 2: Retrieval (reuse async logic from get_answer_async)
        try:
            if use_multi_step is None:
                use_multi_step = settings.rag.USE_MULTI_STEP_QUERY

            simple = self._is_simple_query(search_query)
            if simple:
                print(f"[INFO] Simple query detected, skipping decomposition")

            if use_multi_step and not simple:
                sub_questions = await asyncio.to_thread(self._decompose_query, search_query)

                if question_category == "course_catalog" and self._is_sequence_question(question):
                    sub_questions = self._prioritize_sequence_queries(
                        sub_questions, search_query, question, max_queries=8
                    )

                docs = await self._retrieve_for_subqueries_async(sub_questions, doc_type_filter)
            else:
                if doc_type_filter:
                    docs = await asyncio.to_thread(
                        self.vector_store.similarity_search,
                        search_query, k=settings.rag.RETRIEVER_K,
                        filter={"doc_type": doc_type_filter}
                    )
                else:
                    docs = await asyncio.to_thread(self.retriever.invoke, search_query)

            # Sequence boost
            if question_category == "course_catalog" and self._is_sequence_question(question):
                section_filters = [{"section": "freeman_core"}, {"section": "sequence"}]
                boosted_docs = []
                for f in section_filters:
                    filt = {"$and": [{"doc_type": "catalog"}, f]}
                    boost = await asyncio.to_thread(
                        self.vector_store.similarity_search,
                        search_query, k=max(6, settings.rag.RETRIEVER_K // 2), filter=filt
                    )
                    boosted_docs.extend(boost)
                if boosted_docs:
                    docs = self._merge_docs(docs, boosted_docs)

            docs = self._augment_management_plan_docs(docs, question, search_query)

            # Keep parity with non-streaming paths: enrich sequence questions
            # with course-entry chunks so per-course credits are easier to cite.
            docs = self._enrich_with_course_entries(docs, question)

            if not docs:
                fallback = (
                    "I'm not seeing that information in the documents I have, but I'm happy to help with anything else! "
                    "For official guidance and questions about how these policies apply to your specific situation, "
                    "please consult with your academic advisor or the Office of the Registrar."
                )
                yield f"event: metadata\ndata: {_json.dumps({'category': question_category, 'citations': []})}\n\n"
                yield f"event: token\ndata: {_json.dumps({'token': fallback})}\n\n"
                yield f"event: done\ndata: {_json.dumps({'answer': fallback, 'citations': [], 'category': question_category})}\n\n"
                return

        except Exception as e:
            print(f"[ERROR] Retrieval error: {e}")
            error_msg = "Sorry, I ran into an error retrieving information. Please try again later or contact support."
            yield f"event: metadata\ndata: {_json.dumps({'category': question_category, 'citations': []})}\n\n"
            yield f"event: token\ndata: {_json.dumps({'token': error_msg})}\n\n"
            yield f"event: done\ndata: {_json.dumps({'answer': error_msg, 'citations': [], 'category': question_category})}\n\n"
            return

        # Build knowledge + citations
        knowledge = self._prepare_knowledge(docs)
        citations = []
        for doc in docs:
            meta = doc.metadata or {}
            src = self._short_source(meta.get("source", "Catalogue"))
            page = (meta.get("page", 0) or 0) + 1
            source_filename = os.path.basename(meta.get("source", "catalog.pdf"))
            doc_type = meta.get("doc_type", "catalog")
            citations.append({
                "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                "source": src, "page": page,
                "url": self._get_document_url(source_filename, page, meta.get("source_url")),
                "doc_type": doc_type,
            })
        citations = self._dedupe_citations(citations)

        # STEP 3: Send metadata event (citations, category) before streaming
        yield f"event: metadata\ndata: {_json.dumps({'category': question_category, 'citations': citations})}\n\n"

        # Build prompt
        history_context = ""
        if conversation_history:
            history_context = "\n".join([
                f"{msg['role'].capitalize()}: {msg['content'][:300]}"
                for msg in conversation_history[-6:]
            ])
        user_prompt = get_user_prompt(
            question, knowledge, history_context if conversation_history else "",
            summary=conversation_summary or None,
            user_profile=user_profile or None,
        )

        messages = [
            SystemMessage(content=self._get_system_prompt(question_category)),
            HumanMessage(content=user_prompt)
        ]

        # STEP 4: Stream tokens via LangChain's astream
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

        # Post-processing on the full answer
        answer = self._normalize_text(full_answer.strip())

        fallback_sentence = (
            "I'm not seeing that information in the documents I have, but I'm happy to help with anything else!"
            "For official guidance and questions about how these policies apply to your specific situation, "
            "please consult with your academic advisor or the Office of the Registrar.")

        # Add disclaimer for catalog and policy responses (sent as final token)
        if answer != fallback_sentence and question_category in ("academic_policy", "course_catalog"):
            yield f"event: token\ndata: {_json.dumps({'token': config.POLICY_DISCLAIMER})}\n\n"
            answer = answer + config.POLICY_DISCLAIMER

        # Generate follow-ups after stream completes
        if answer and answer != fallback_sentence:
            try:
                followups = await asyncio.to_thread(self._generate_followups, question, answer, conversation_history)
                yield f"event: followups\ndata: {_json.dumps({'follow_ups': followups})}\n\n"
            except Exception as e:
                print(f"[WARNING] Follow-up generation failed: {e}")
                yield f"event: followups\ndata: {_json.dumps({'follow_ups': []})}\n\n"
        else:
            yield f"event: followups\ndata: {_json.dumps({'follow_ups': []})}\n\n"

        # Yield the done event — the route handler will save to DB and send `saved` event
        yield f"event: done\ndata: {_json.dumps({'answer': answer, 'citations': citations, 'category': question_category})}\n\n"


# Global instance with lazy initialization
_chatbot_service_instance = None

def get_chatbot_service() -> ChatbotService:
    """Get or create the global chatbot service instance (lazy initialization).

    Returns:
        ChatbotService: The singleton instance of ChatbotService.
    """
    global _chatbot_service_instance
    if _chatbot_service_instance is None:
        _chatbot_service_instance = ChatbotService()
    return _chatbot_service_instance

# For backward compatibility
chatbot_service = None  # Will be initialized on first use
