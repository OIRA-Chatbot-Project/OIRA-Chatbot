from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.messages import SystemMessage, HumanMessage
from typing import List, Dict, Tuple, Optional, AsyncGenerator
import os
import re
import json
import asyncio
import config
from prompts import get_decompose_prompt, get_user_prompt, get_contextualize_prompt, get_question_classifier_prompt, SYSTEM_PROMPT
from logger import get_logger
from utils import extract_json_from_text, extract_json_array_from_text

logger = get_logger(__name__)

class ChatbotService:
    """Service for handling chatbot RAG operations"""
    
    def __init__(self):
        """Initialize the chatbot service with embeddings and vector store"""
        # Initialize embeddings model
        self.embeddings_model = OpenAIEmbeddings(model=config.EMBEDDING_MODEL)
        
        # Initialize LLM with modest temperature for factual responses
        self.llm = ChatOpenAI(
            temperature=0.3,
            model=config.OPENAI_MODEL
        )
        
        # Initialize a separate LLM for query decomposition (lower temperature)
        self.decompose_llm = ChatOpenAI(
            temperature=0.1,
            model=config.OPENAI_MODEL
        )

        # Initialize a separate LLM for question classification (very low temperature)
        self.classifier_llm = ChatOpenAI(
            temperature=config.QUESTION_CLASSIFIER_TEMPERATURE,
            model=config.OPENAI_MODEL
        )

        # Connect to ChromaDB
        self.vector_store = Chroma(
            collection_name=config.CHROMA_COLLECTION_NAME,
            embedding_function=self.embeddings_model,
            persist_directory=config.CHROMA_PATH,
        )
        
        # Set up retriever with MMR for diverse but relevant chunks
        self.retriever = self.vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": config.RETRIEVER_K,
                "fetch_k": config.RETRIEVER_FETCH_K,
                "lambda_mult": config.RETRIEVER_LAMBDA_MULT
            }
        )
    
    def _short_source(self, path: str) -> str:
        """Turn a long file path into a friendly filename for citations."""
        if not path:
            return "Source"
        name = os.path.basename(path)
        return name.replace("_", " ")

    def _classify_question(self, question: str) -> str:
        """
        Classify a question as 'course_catalog', 'academic_policy', or 'off_topic'.

        This pre-retrieval classification allows us to:
        1. Reject off-topic questions immediately
        2. Filter ChromaDB searches to relevant document types

        Args:
            question: The user's question

        Returns:
            One of: 'course_catalog', 'academic_policy', 'off_topic'
            Falls back to 'course_catalog' on error
        """
        if not config.ENABLE_OFF_TOPIC_DETECTION:
            # Classification disabled - default to catalog
            return "course_catalog"

        classifier_prompt = get_question_classifier_prompt(question)

        try:
            response = self.classifier_llm.invoke(classifier_prompt)
            response_text = response.content.strip()

            # Extract JSON using shared utility
            data = extract_json_from_text(response_text)
            if data:
                category = data.get("category", "course_catalog")

                # Validate category
                if category in ["course_catalog", "academic_policy", "off_topic"]:
                    logger.info(f"Question classified as: {category}")
                    return category
                else:
                    logger.warning(f"Invalid category '{category}', defaulting to 'course_catalog'")
                    return "course_catalog"

        except Exception as e:
            logger.warning(f"Question classification failed: {e}. Defaulting to 'course_catalog'")

        # Fallback to catalog (safer than rejecting)
        return "course_catalog"

    def _get_document_url(self, source_filename: str, page: int) -> str:
        """
        This is for the Reference block under each answer.
        Generate appropriate URL for a document citation based on its source.

        Args:
            source_filename: Base filename (e.g., "GRADE REPLACEMENT POLICY.pdf")
            page: Page number (1-indexed)

        Returns:
            URL string for frontend to link to
        """
        # Clean filename for URL (remove spaces, special chars)
        url_safe_filename = source_filename.replace(" ", "%20")

        # Use configurable PDF base URL instead of hardcoded localhost
        return f"{config.PDF_BASE_URL}/{url_safe_filename}#page={page}"

    def _prepare_knowledge(self, docs) -> str:
        """
        Build a labeled context string so the model can cite pages.
        Each chunk gets headers before and after for better citation tracking.
        """
        parts = []
        for d in docs:
            meta = d.metadata or {}
            src = self._short_source(meta.get("source", "Catalogue"))
            # PyPDFDirectoryLoader is 0-based; add 1 for human-friendly
            page = (meta.get("page", 0) or 0) + 1
            header = f"[{src}, p. {page}]"
            # Add header before and after for better citation tracking
            parts.append(f"{header}\n{d.page_content.strip()}\n{header}\n")
        return "\n".join(parts)
    
    def _decompose_query(self, question: str) -> List[str]:
        """
        Decompose a complex query into multiple sub-questions using structured JSON output.
        This helps with comparison queries, multi-part questions, and complex reasoning.
        
        Args:
            question: The original user question
            
        Returns:
            List of sub-questions (or single question if decomposition not needed)
        """
        decompose_prompt = get_decompose_prompt(question)

        try:
            response = self.decompose_llm.invoke(decompose_prompt)
            response_text = response.content.strip()
            
            # Extract JSON using shared utility
            data = extract_json_from_text(response_text)
            if data:
                # Handle different response types
                if data.get("type") == "simple" or not data.get("sub_questions"):
                    return [question]
                
                if data.get("type") == "too_broad":
                    suggestion = data.get("suggestion", "Please narrow your question.")
                    logger.warning(f"Query too broad. Suggestion: {suggestion}")
                    return [question]

                sub_questions = data.get("sub_questions", [])
                if isinstance(sub_questions, list) and sub_questions:
                    if len(sub_questions) > 5:
                        logger.warning(f"Too many sub-questions ({len(sub_questions)}). Limiting to first 5.")
                        sub_questions = sub_questions[:5]
                    return sub_questions

        except Exception as e:
            logger.warning(f"Query decomposition failed: {e}. Using original question.")
        
        # Fallback to original question
        return [question]
    
    def _retrieve_for_subqueries(self, sub_questions: List[str], doc_type_filter: Optional[str] = None) -> List:
        """
        Retrieve documents for multiple sub-questions with adaptive allocation.

        Strategy:
        1. Guarantee minimum documents per sub-question
        2. Distribute remaining budget proportionally
        3. Use round-robin for balanced representation

        Args:
            sub_questions: List of sub-questions to retrieve for
            doc_type_filter: Optional document type to filter by ('catalog' or 'policy')

        Returns:
            Combined list of unique documents
        """
        num_subqueries = len(sub_questions)
        if num_subqueries == 0:
            return []
        
        # Calculate adaptive retrieval limits
        min_per_query = config.MIN_DOCS_PER_SUBQUERY
        total_min = min_per_query * num_subqueries
        
        # Adjust strategy based on number of sub-questions
        if total_min > config.MAX_MULTI_STEP_DOCS:
            min_per_query = max(2, config.MAX_MULTI_STEP_DOCS // num_subqueries)
            logger.info(f"Many sub-questions ({num_subqueries}). Adjusting to {min_per_query} docs minimum per query.")
        
        # Retrieve documents for each sub-question
        docs_per_question = []
        for sub_q in sub_questions:
            try:
                # Apply doc_type filter if specified
                if doc_type_filter:
                    docs = self.vector_store.similarity_search(
                        sub_q,
                        k=config.RETRIEVER_K,
                        filter={"doc_type": doc_type_filter}
                    )
                else:
                    docs = self.retriever.invoke(sub_q)
                docs_per_question.append(docs)
            except Exception as e:
                logger.warning(f"Retrieval failed for sub-query '{sub_q}': {e}")
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
                    
                    if len(all_docs) >= config.MAX_MULTI_STEP_DOCS:
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
                        
                        if len(all_docs) >= config.MAX_MULTI_STEP_DOCS:
                            logger.debug(f"Document distribution: {dict(zip(range(1, num_subqueries+1), docs_count_per_query))}")
                            return all_docs

        logger.debug(f"Final document distribution: {dict(zip(range(1, num_subqueries+1), docs_count_per_query))}")
        return all_docs

    def _merge_docs(self, base_docs: List, extra_docs: List) -> List:
        """Merge document lists, de-duplicating by (source, page)."""
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
        """
        Build a contextual query that incorporates conversation history for better follow-up handling.

        Args:
            question: Current user question
            conversation_history: Previous conversation turns

        Returns:
            Standalone query that includes necessary context
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
            logger.warning(f"Contextualization failed: {e}. Using original question.")

        return question

    async def _classify_question_async(self, question: str) -> str:
        """
        Async version of question classification.
        Classify a question as 'course_catalog', 'academic_policy', or 'off_topic'.
        """
        if not config.ENABLE_OFF_TOPIC_DETECTION:
            return "course_catalog"

        classifier_prompt = get_question_classifier_prompt(question)

        try:
            response = await self.classifier_llm.ainvoke(classifier_prompt)
            response_text = response.content.strip()

            # Extract JSON using shared utility
            data = extract_json_from_text(response_text)
            if data:
                category = data.get("category", "course_catalog")
                if category in ["course_catalog", "academic_policy", "off_topic"]:
                    logger.info(f"Question classified as: {category}")
                    return category
                else:
                    logger.warning(f"Invalid category '{category}', defaulting to 'course_catalog'")
                    return "course_catalog"

        except Exception as e:
            logger.warning(f"Question classification failed: {e}. Defaulting to 'course_catalog'")

        return "course_catalog"

    async def _build_contextual_query_async(self, question: str, conversation_history: List[Dict[str, str]]) -> str:
        """
        Async version of contextual query building.
        """
        if not conversation_history:
            return question

        recent_history = conversation_history[-6:]
        if not recent_history:
            return question

        history_text = "\n".join([
            f"{msg['role'].capitalize()}: {msg['content'][:150]}"
            for msg in recent_history
        ])

        contextualize_prompt = get_contextualize_prompt(question, history_text)

        try:
            response = await self.decompose_llm.ainvoke(contextualize_prompt)
            contextual_query = response.content.strip()

            if contextual_query and len(contextual_query) > 10:
                return contextual_query
        except Exception as e:
            logger.warning(f"Contextualization failed: {e}. Using original question.")

        return question

    def _is_simple_question(self, question: str) -> bool:
        """
        Determine if a question is simple enough to skip query decomposition.
        Simple questions are short, direct questions without comparisons or lists.

        Args:
            question: The user's question

        Returns:
            True if the question is simple and should skip decomposition
        """
        words = question.split()

        # Short questions (< 15 words) are likely simple
        if len(words) < 15:
            # Check for comparison/complex keywords that indicate decomposition is needed
            comparison_keywords = [
                'compare', 'difference', 'between', 'versus', 'vs',
                'both', 'all', 'each', 'every', 'multiple',
                'list', 'what are the', 'how many', 'which ones'
            ]
            question_lower = question.lower()
            if not any(kw in question_lower for kw in comparison_keywords):
                # Also check for multiple course codes or majors (indicates comparison)
                course_pattern = r'[A-Z]{2,4}\s*\d{3}'
                matches = re.findall(course_pattern, question.upper())
                if len(matches) <= 1:
                    return True

        return False

    def _is_sequence_question(self, question: str) -> bool:
        """Heuristic check for questions asking about a major/course sequence or plan."""
        q = question.lower()
        return any(
            key in q
            for key in (
                "sequence",
                "four-year",
                "four year",
                "plan",
                "recommended sequence",
                "curriculum",
            )
        )

    def _expand_sequence_queries(self, base_query: str, question: str) -> List[str]:
        """
        Expand sequence-style questions with related retrieval queries.
        Keeps expansions short and catalog-focused to avoid off-topic noise.
        """
        expansions = [
            base_query,
            f"{base_query} recommended sequence",
            f"{base_query} four-year plan",
            f"{base_query} major requirements",
            f"{base_query} core curriculum",
            "culminating experience",
        ]

        q_lower = question.lower()
        if "freeman" in q_lower or "business analytics" in q_lower or "bsba" in q_lower:
            expansions.append("Freeman College core curriculum")

        # De-duplicate while preserving order
        seen = set()
        deduped = []
        for q in expansions:
            if q not in seen:
                seen.add(q)
                deduped.append(q)
        return deduped

    def _generate_followups(self, question: str, answer: str, conversation_history: List[Dict[str, str]]) -> List[str]:
        """
        Generate up to 5 suggested follow-up questions tailored to the user's context
        present in the conversation history. Returns a list of suggestion strings.
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

            # Extract JSON array using shared utility
            suggestions = extract_json_array_from_text(resp_text)
            if suggestions:
                # Clean and limit to 5
                suggestions = [s.strip() for s in suggestions if isinstance(s, str)]
                if len(suggestions) > 5:
                    suggestions = suggestions[:5]
                return suggestions
        except Exception as e:
            logger.warning(f"Follow-up generation failed: {e}")

        # Fallback: simple heuristic suggestions
        fallback = [
            "Can you clarify what you meant by that?",
            "Do you want more details about any specific course or policy mentioned?",
            "Would you like recommendations based on your major or year?"
        ]
        return fallback[:3]
    
    def get_answer(self, question: str, conversation_history: List[Dict[str, str]], use_multi_step: Optional[bool] = None) -> Tuple[str, List[Dict], str, List[str]]:
        """
        Get an answer to a question using RAG with optional multi-step query decomposition.
        Now includes question classification and document type filtering.

        Args:
            question: The user's question
            conversation_history: List of previous messages with 'role' and 'content'
            use_multi_step: Whether to use multi-step query decomposition (default: from config)

        Returns:
            Tuple of (answer, citations, question_category)
        """
        # STEP 1: Classify the question
        question_category = self._classify_question(question)

        # STEP 2: Reject off-topic questions immediately
        if question_category == "off_topic":
            logger.info(f"Off-topic question rejected: {question[:100]}")
            return (
                config.OFF_TOPIC_MESSAGE,
                [],
                "off_topic",
                []
            )

        # STEP 3: Determine document type filter
        doc_type_filter = None
        if question_category == "course_catalog":
            doc_type_filter = "catalog"
        elif question_category == "academic_policy":
            doc_type_filter = "policy"

        logger.debug(f"Filtering retrieval to doc_type: {doc_type_filter}")

        try:
            # Use config default if not specified
            if use_multi_step is None:
                use_multi_step = config.USE_MULTI_STEP_QUERY

            # Build contextual query for better follow-up handling
            search_query = self._build_contextual_query(question, conversation_history)
            logger.info(f"Retrieval start | category={question_category} | multi_step={use_multi_step}")

            # STEP 4: Decompose query if needed and enabled
            if use_multi_step:
                sub_questions = self._decompose_query(search_query)
                logger.debug(f"Sub-questions: {len(sub_questions)}")

                if len(sub_questions) >= 4:
                    logger.warning(f"High number of sub-questions ({len(sub_questions)}). Results may be limited per topic.")

                # Expand sequence questions for broader recall
                if question_category == "course_catalog" and self._is_sequence_question(question):
                    expanded = self._expand_sequence_queries(search_query, question)
                    sub_questions = sub_questions + expanded
                    # Cap to avoid over-fetching
                    if len(sub_questions) > 8:
                        sub_questions = sub_questions[:8]

                # Retrieve documents for all sub-questions WITH FILTERING
                docs = self._retrieve_for_subqueries(sub_questions, doc_type_filter)
            else:
                # Single-step retrieval WITH FILTERING
                if doc_type_filter:
                    docs = self.vector_store.similarity_search(
                        search_query,
                        k=config.RETRIEVER_K,
                        filter={"doc_type": doc_type_filter}
                    )
                else:
                    docs = self.retriever.invoke(search_query)
            logger.info(f"Retrieved {len(docs)} documents")

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
                            k=max(6, config.RETRIEVER_K // 2),
                            filter=filt
                        )
                    )
                if boosted_docs:
                    docs = self._merge_docs(docs, boosted_docs)
                    logger.debug(f"Boosted docs added: {len(boosted_docs)}, total: {len(docs)}")

            # Handle no results
            if not docs:
                fallback_message = (
                    "I'm not seeing that information in the documents I have, but I'm happy to help with anything else! "
                    "For official guidance and questions about how these policies apply to your specific situation, please consult with your academic advisor or the Office of the Registrar."
                )
                if question_category == "academic_policy":
                    fallback_message = (
                        "I couldn't find relevant policy information. "
                        "Please contact the Office of the Registrar or your academic advisor for guidance on this policy question."
                    )
                return (
                    fallback_message,
                    [],
                    question_category,
                    []
                )
        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            return (
                "Sorry, I ran into an error retrieving information. "
                "Please try again later or contact support.",
                [],
                question_category,
                []
            )

        # Build knowledge base with page citations
        knowledge = self._prepare_knowledge(docs)

        # Build citations list for API response
        citations = []
        for doc in docs:
            meta = doc.metadata or {}
            src = self._short_source(meta.get("source", "Catalogue"))
            # PyPDFDirectoryLoader is 0-based; add 1 for human-friendly
            page = (meta.get("page", 0) or 0) + 1
            source_filename = os.path.basename(meta.get("source", "catalog.pdf"))
            doc_type = meta.get("doc_type", "catalog")

            citation = {
                "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                "source": src,
                "page": page,
                "url": self._get_document_url(source_filename, page),
                "doc_type": doc_type  # Include for frontend filtering/display
            }
            citations.append(citation)

        # Format conversation history for context
        history_context = ""
        if conversation_history:
            history_context = "\n".join([
                f"{msg['role'].capitalize()}: {msg['content'][:300]}"  # Truncate long messages
                for msg in conversation_history[-6:]  # Last 3 exchanges
            ])

        # Build prompt using system/user message separation
        user_prompt = get_user_prompt(question, knowledge, history_context if conversation_history else "")

        try:
            # Use system/user message structure
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=user_prompt)
            ]

            response = self.llm.invoke(messages)
            answer = response.content

            # If the model appended the generic fallback sentence but we have citations,
            # remove the fallback to avoid redundant/contradictory text. The fallback
            # is required when KNOWLEDGE lacks the requested info, but we already
            # retrieved citations for this answer.
            fallback_sentence = (
                "I'm not able to find that information in the documents I have here. "
                "Please contact your academic advisor or the Office of the Registrar for assistance."
            )
            if fallback_sentence in answer and citations and len(citations) > 0:
                answer = answer.replace(fallback_sentence, '').strip()

            # Add policy disclaimer if this is a policy question
            if question_category == "academic_policy":
                answer = answer + config.POLICY_DISCLAIMER

            # Generate follow-up suggestions tailored to the user's context
            followups = self._generate_followups(question, answer, conversation_history)

            return answer, citations, question_category, followups  # type: ignore

        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return (
                "Sorry, I encountered an error generating a response. "
                "Please try again or contact your academic advisor.",
                citations,
                question_category,
                []
            )

    def get_answer_without_followups(self, question: str, conversation_history: List[Dict[str, str]], use_multi_step: Optional[bool] = None) -> Tuple[str, List[Dict], str]:
        """
        Get an answer without generating follow-up suggestions (for faster response).
        Follow-ups can be generated separately in a background task.

        Args:
            question: The user's question
            conversation_history: List of previous messages with 'role' and 'content'
            use_multi_step: Whether to use multi-step query decomposition

        Returns:
            Tuple of (answer, citations, question_category)
        """
        answer, citations, category, _ = self.get_answer(question, conversation_history, use_multi_step)
        return answer, citations, category

    async def stream_answer(
        self,
        question: str,
        conversation_history: List[Dict[str, str]],
        use_multi_step: Optional[bool] = None
    ) -> AsyncGenerator[Dict, None]:
        """
        Stream the answer token by token for faster perceived response time.

        Yields dictionaries with:
        - {"type": "metadata", "citations": [...], "category": "..."}
        - {"type": "token", "content": "..."}
        - {"type": "done", "full_answer": "..."}

        Args:
            question: The user's question
            conversation_history: List of previous messages
            use_multi_step: Whether to use multi-step query decomposition
        """
        # STEP 1: Run classification and contextualization in PARALLEL
        category, search_query = await asyncio.gather(
            self._classify_question_async(question),
            self._build_contextual_query_async(question, conversation_history)
        )

        # STEP 2: Handle off-topic questions
        if category == "off_topic":
            logger.info(f"Off-topic question rejected: {question[:100]}")
            yield {"type": "metadata", "citations": [], "category": "off_topic"}
            yield {"type": "token", "content": config.OFF_TOPIC_MESSAGE}
            yield {"type": "done", "full_answer": config.OFF_TOPIC_MESSAGE}
            return

        # STEP 3: Determine document type filter
        doc_type_filter = None
        if category == "course_catalog":
            doc_type_filter = "catalog"
        elif category == "academic_policy":
            doc_type_filter = "policy"

        logger.info(f"Streaming | category={category} | doc_type={doc_type_filter}")

        # Use config default if not specified
        if use_multi_step is None:
            use_multi_step = config.USE_MULTI_STEP_QUERY

        try:
            # STEP 4: Smart skip - check if we should decompose
            should_decompose = use_multi_step and not self._is_simple_question(question)

            if should_decompose:
                sub_questions = self._decompose_query(search_query)
                logger.debug(f"Sub-questions: {len(sub_questions)}")

                # Expand sequence questions
                if category == "course_catalog" and self._is_sequence_question(question):
                    expanded = self._expand_sequence_queries(search_query, question)
                    sub_questions = sub_questions + expanded
                    if len(sub_questions) > 8:
                        sub_questions = sub_questions[:8]

                docs = self._retrieve_for_subqueries(sub_questions, doc_type_filter)
            else:
                # Simple question - direct retrieval
                logger.debug("Simple question - skipping decomposition")
                if doc_type_filter:
                    docs = self.vector_store.similarity_search(
                        search_query,
                        k=config.RETRIEVER_K,
                        filter={"doc_type": doc_type_filter}
                    )
                else:
                    docs = self.retriever.invoke(search_query)

            logger.info(f"Retrieved {len(docs)} documents")

            # Sequence question boosting
            if category == "course_catalog" and self._is_sequence_question(question):
                section_filters = [{"section": "freeman_core"}, {"section": "sequence"}]
                boosted_docs = []
                for f in section_filters:
                    filt = {"$and": [{"doc_type": "catalog"}, f]}
                    boosted_docs.extend(
                        self.vector_store.similarity_search(
                            search_query,
                            k=max(6, config.RETRIEVER_K // 2),
                            filter=filt
                        )
                    )
                if boosted_docs:
                    docs = self._merge_docs(docs, boosted_docs)

            # Handle no results
            if not docs:
                fallback_message = (
                    "I'm not seeing that information in the documents I have, but I'm happy to help with anything else! "
                    "For official guidance, please consult your academic advisor or the Office of the Registrar."
                )
                yield {"type": "metadata", "citations": [], "category": category}
                yield {"type": "token", "content": fallback_message}
                yield {"type": "done", "full_answer": fallback_message}
                return

        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            error_message = "Sorry, I ran into an error retrieving information. Please try again later."
            yield {"type": "metadata", "citations": [], "category": category}
            yield {"type": "token", "content": error_message}
            yield {"type": "done", "full_answer": error_message}
            return

        # Build knowledge and citations
        knowledge = self._prepare_knowledge(docs)

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
                "url": self._get_document_url(source_filename, page),
                "doc_type": doc_type
            }
            citations.append(citation)

        # STEP 5: Yield metadata first (citations available immediately)
        yield {"type": "metadata", "citations": citations, "category": category}

        # Format conversation history
        history_context = ""
        if conversation_history:
            history_context = "\n".join([
                f"{msg['role'].capitalize()}: {msg['content'][:300]}"
                for msg in conversation_history[-6:]
            ])

        # Build prompt
        user_prompt = get_user_prompt(question, knowledge, history_context if conversation_history else "")

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_prompt)
        ]

        # STEP 6: Stream the LLM response
        full_answer = ""
        try:
            async for chunk in self.llm.astream(messages):
                token = chunk.content or ""
                if token:
                    full_answer += token
                    yield {"type": "token", "content": token}

            # Clean up the answer
            fallback_sentence = (
                "I'm not seeing that information in the documents I have, but I'm happy to help with anything else!"
                "For official guidance and questions about how these policies apply to your specific situation, please consult with your academic advisor or the Office of the Registrar."
            )

            if fallback_sentence in full_answer and citations:
                if full_answer.strip() != fallback_sentence:
                    full_answer = full_answer.replace(fallback_sentence, '').strip()

            # Add policy disclaimer if applicable
            if category == "academic_policy" and full_answer and fallback_sentence not in full_answer:
                disclaimer = config.POLICY_DISCLAIMER
                yield {"type": "token", "content": disclaimer}
                full_answer += disclaimer

            yield {"type": "done", "full_answer": full_answer}

        except Exception as e:
            logger.error(f"LLM streaming error: {e}")
            error_message = "Sorry, I encountered an error generating a response."
            yield {"type": "token", "content": error_message}
            yield {"type": "done", "full_answer": error_message}

    def recommend_courses_from_schedule(self, schedule_summary: str, conversation_history: List[Dict[str, str]]) -> Tuple[str, List[Dict], str, List[str]]:
        """
        Provide course recommendations using a student's prior schedule summary.
        Returns tuple of (answer, citations, question_category, followups).
        """
        question = (
            "A student shared their previously completed courses and experiences:\n"
            f"{schedule_summary}\n\n"
            "Using the Bucknell course catalog, recommend 4-6 thoughtful next courses that build on this plan. "
            "Group suggestions by category when possible (Major requirements, Core/Electives, Exploratory). "
            "Consider prerequisites and avoid recommending courses that appear to already be completed."
        )
        return self.get_answer(question, conversation_history)


# Global instance with lazy initialization
_chatbot_service_instance = None

def get_chatbot_service() -> ChatbotService:
    """Get or create the global chatbot service instance (lazy initialization)"""
    global _chatbot_service_instance
    if _chatbot_service_instance is None:
        _chatbot_service_instance = ChatbotService()
    return _chatbot_service_instance
