from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.messages import SystemMessage, HumanMessage
from typing import List, Dict, Tuple, Optional
import os
import re
import json
import config

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
        decompose_prompt = f"""You are an academic advising assistant. Analyze the student's question and determine if it needs to be broken down into multiple sub-questions for better retrieval and answering.

DECOMPOSITION CRITERIA:
1. Comparison questions (e.g., "Compare X and Y", "What's the difference between A and B")
2. Multi-part questions with "and" (e.g., "What are prerequisites and what comes after?")
3. Conditional questions (e.g., "If I do X, then what about Y?")
4. Questions requiring information from multiple sources

IMPORTANT CONSTRAINTS:
- Maximum 5 sub-questions (prefer 2-4 for best results)
- If question asks about 6+ items, group them or suggest user be more specific
- Each sub-question needs sufficient retrieval budget

Return JSON ONLY. No other text.

If the question is SIMPLE and direct (e.g., "What is CSCI 204?"), respond:
{{"type": "simple", "sub_questions": []}}

If the question is COMPLEX but manageable (2-5 topics), break it into specific sub-questions:
{{"type": "complex", "sub_questions": ["sub-question 1", "sub-question 2", ...]}}

If the question is TOO BROAD (6+ items or very general), suggest clarification:
{{"type": "too_broad", "suggestion": "This question covers many topics. Please ask about 2-3 specific courses/requirements."}}

Each sub-question should:
- Be self-contained and answerable independently
- Focus on one specific aspect
- Include relevant context (course codes, major names, etc.)

QUESTION: {question}

JSON RESPONSE:"""

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
    
    def _retrieve_for_subqueries(self, sub_questions: List[str]) -> List:
        """
        Retrieve documents for multiple sub-questions with adaptive allocation.
        
        Strategy:
        1. Guarantee minimum documents per sub-question
        2. Distribute remaining budget proportionally
        3. Use round-robin for balanced representation
        
        Args:
            sub_questions: List of sub-questions to retrieve for
            
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
            # Too many sub-questions - reduce minimum guarantee
            min_per_query = max(2, config.MAX_MULTI_STEP_DOCS // num_subqueries)
            print(f"[INFO] Many sub-questions ({num_subqueries}). Adjusting to {min_per_query} docs minimum per query.")
        
        # Retrieve documents for each sub-question
        docs_per_question = []
        for sub_q in sub_questions:
            try:
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
                            # Log distribution for debugging
                            print(f"[INFO] Document distribution: {dict(zip(range(1, num_subqueries+1), docs_count_per_query))}")
                            return all_docs
        
        print(f"[INFO] Final document distribution: {dict(zip(range(1, num_subqueries+1), docs_count_per_query))}")
        return all_docs
    
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
        
        contextualize_prompt = f"""Given the conversation history below and a new user question, rewrite the question as a standalone query that includes all necessary context.

If the question is already self-contained, return it as-is.
If it refers to previous context (e.g., "What about prerequisites for that?"), incorporate the context to make it standalone.

Return ONLY the rewritten question, nothing else.

CONVERSATION HISTORY:
{history_text}

NEW QUESTION: {question}

STANDALONE QUESTION:"""
        
        try:
            response = self.decompose_llm.invoke(contextualize_prompt)
            contextual_query = response.content.strip()
            
            # Validate that we got a reasonable response
            if contextual_query and len(contextual_query) > 10:
                return contextual_query
        except Exception as e:
            print(f"[WARNING] Contextualization failed: {e}. Using original question.")
        
        return question
    
    def get_answer(self, question: str, conversation_history: List[Dict[str, str]], use_multi_step: Optional[bool] = None) -> Tuple[str, List[Dict]]:
        """
        Get an answer to a question using RAG with optional multi-step query decomposition
        
        Args:
            question: The user's question
            conversation_history: List of previous messages with 'role' and 'content'
            use_multi_step: Whether to use multi-step query decomposition (default: from config)
        
        Returns:
            Tuple of (answer, citations)
        """
        try:
            # Use config default if not specified
            if use_multi_step is None:
                use_multi_step = config.USE_MULTI_STEP_QUERY
            
            # Build contextual query for better follow-up handling
            search_query = self._build_contextual_query(question, conversation_history)
            
            # Step 1: Decompose query if needed and enabled
            if use_multi_step:
                sub_questions = self._decompose_query(search_query)
                
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
                
                # Retrieve documents for all sub-questions
                docs = self._retrieve_for_subqueries(sub_questions)
            else:
                # Single-step retrieval
                docs = self.retriever.invoke(search_query)
            
            # Handle no results
            if not docs:
                return (
                    "I couldn't retrieve relevant catalog sections. "
                    "Please try rephrasing (e.g., include a course code like CSCI 204) "
                    "or contact your academic advisor for assistance.",
                    []
                )
        except Exception as e:
            print(f"[ERROR] Retrieval error: {e}")
            return (
                "Sorry, I ran into an error retrieving catalog information. "
                "Please try again later or contact support.",
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
            
            citation = {
                "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                "source": src,
                "page": page
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
        system_prompt = """You are the Bucknell University Academic Catalogue Virtual Assistant.

YOUR ONLY SOURCE OF TRUTH
- You may ONLY use information that appears in the KNOWLEDGE section below.
- You may NOT use outside knowledge, assumptions, or “typical patterns.”
- Do NOT infer or guess requirements, prerequisites, or policies.
- If the KNOWLEDGE does not clearly contain the requested information, you MUST respond exactly with:
  "I'm not able to find that information in the catalog snippets I have here. Please contact your academic advisor or consult the full catalog."

IF INFORMATION IS PARTIAL OR UNCLEAR
- If KNOWLEDGE is related but does not fully answer the question, state clearly what IS known and then use the required fallback sentence above.
- If there are conflicts or contradictions in KNOWLEDGE, say that the information appears inconsistent and use the fallback sentence above.

STYLE & FORMAT
- Be professional, warm, and student-centered.
- Use short bullet points for:
  - Requirements
  - Steps
  - Recommended courses or options
- Keep answers under 300 words unless the question explicitly asks for exhaustive detail.
- Do NOT repeat the entire question; summarize it briefly only if needed for clarity.

<<<<<<< HEAD
Course Recommendation Guidance (when applicable):
- Prioritize courses aligned with the student's major/concentration/interests.
- Verify prerequisites before recommending.
- Recommend a balanced load (major/core + gen ed + electives).
- Consider student's year (100-level for first-years, then 200/300 etc.).
- Don't suggest courses already completed or their prerequisites; suggest the next level instead.
- List suggested courses in ascending order (100–500).
- If you see course names adjacent to numbers, treat numbers under a ‘Credits’ column as credits, not part of the course name
=======
CITATIONS
- Every factual statement drawn from KNOWLEDGE should be supportable by a citation.
- Include page citations by copying the bracket tags from the relevant chunks, for example:
  [2025-2026 course catalog.pdf, p. 367]
- Place citations immediately after the relevant sentence or bullet.
- If multiple chunks support a statement, one citation is enough.
>>>>>>> e297f7b6bdc8620cccc072fe3c30413ecaaed842

COURSE RECOMMENDATIONS (WHEN APPLICABLE)
When recommending courses (e.g., “What should I take next?”):
- Prioritize courses aligned with the student’s major, concentration, and/or stated interests, as explicitly shown in KNOWLEDGE.
- Verify prerequisites in KNOWLEDGE before recommending a course.
- Recommend a balanced schedule (major/core + general education + electives) only if KNOWLEDGE provides enough detail to do so.
- Consider course level by student year (100-level for most first-years, then 200/300, etc.) only when KNOWLEDGE explicitly supports these patterns.
- Do NOT recommend courses that KNOWLEDGE indicates are already completed; suggest the next appropriate level instead.
- List suggested courses in ascending course number order (100–500) when possible.
- If you cannot verify prerequisites, requirements, or completion history from KNOWLEDGE, say so and use the fallback sentence.

HALLUCINATION PREVENTION
- Never invent or guess:
  - Course codes
  - Course names
  - Requirements
  - Policies
  - Counts (e.g., “you must take 3 courses”) that are not explicitly stated in KNOWLEDGE.
- Avoid phrases like “typically,” “usually,” or “in general.”
- If you are uncertain whether KNOWLEDGE supports a statement, you MUST omit the statement and use the fallback sentence instead.

FINAL CHECK BEFORE ANSWERING
Before sending your answer, mentally verify:
- Every factual claim is directly supported by KNOWLEDGE.
- All necessary citations are present.
- You have used the exact fallback sentence if the answer is missing or incomplete in KNOWLEDGE."""


        user_prompt = f"""QUESTION:
{question}

{f"CONVERSATION HISTORY:\n{history_context}\n" if history_context else ""}
KNOWLEDGE (catalog snippets with citation tags):
{knowledge}"""

        try:
            # Use system/user message structure
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            answer = response.content
            
            return answer, citations  # type: ignore
            
        except Exception as e:
            print(f"[ERROR] LLM generation error: {e}")
            return (
                "Sorry, I encountered an error generating a response. "
                "Please try again or contact your academic advisor.",
                citations
            )

    def recommend_courses_from_schedule(self, schedule_summary: str, conversation_history: List[Dict[str, str]]) -> Tuple[str, List[Dict]]:
        """
        Provide course recommendations using a student's prior schedule summary.
        """
        question = (
            "A student shared their previously completed courses and experiences:\n"
            f"{schedule_summary}\n\n"
            "Using the Bucknell course catalog, recommend 4-6 thoughtful next courses that build on this plan. "
            "Group suggestions by category when possible (Major requirements, Core/Electives, Exploratory). "
            "Consider prerequisites and avoid recommending courses that appear to already be completed."
        )
        return self.get_answer(question, conversation_history)


# Global instance
chatbot_service = ChatbotService()
