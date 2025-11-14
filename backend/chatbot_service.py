from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from typing import List, Dict, Tuple
import os
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
        
        # Connect to ChromaDB
        self.vector_store = Chroma(
            collection_name=config.CHROMA_COLLECTION_NAME,
            embedding_function=self.embeddings_model,
            persist_directory=config.CHROMA_PATH,
        )
        
        # Set up retriever with MMR for diverse but relevant chunks
        self.retriever = self.vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 8, "fetch_k": 50, "lambda_mult": 0.4}
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
        Each chunk gets a header like:
        [2025-2026 course catalog.pdf, p. 367]
        <chunk text>
        """
        parts = []
        for d in docs:
            meta = d.metadata or {}
            src = self._short_source(meta.get("source", "Catalogue"))
            # PyPDFDirectoryLoader is 0-based; add 1 for human-friendly
            page = (meta.get("page", 0) or 0) + 1
            header = f"[{src}, p. {page}]"
            parts.append(f"{header}\n{d.page_content.strip()}\n")
        return "\n".join(parts)
    
    def get_answer(self, question: str, conversation_history: List[Dict[str, str]]) -> Tuple[str, List[Dict]]:
        """
        Get an answer to a question using RAG
        
        Args:
            question: The user's question
            conversation_history: List of previous messages with 'role' and 'content'
        
        Returns:
            Tuple of (answer, citations)
        """
        # Retrieve relevant chunks using MMR
        docs = self.retriever.invoke(question)
        
        # Handle no results
        if not docs:
            return (
                "I couldn't retrieve relevant catalog sections. "
                "Please try rephrasing (e.g., include a course code like CSCI 204) "
                "or check that the PDF is ingested.",
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
        
        # Format conversation history for context (optional, not used in retrieval)
        history_context = ""
        if conversation_history:
            history_context = "\n".join([
                f"{msg['role'].capitalize()}: {msg['content']}"
                for msg in conversation_history[-6:]  # Last 3 exchanges (6 messages)
            ])
        
        # Build RAG prompt with improved instructions
        rag_prompt = f"""
You are the Bucknell University Academic Catalogue Virtual Assistant.
Answer ONLY using the content below in *Knowledge*. Do NOT use outside knowledge.
If the answer is not explicitly supported, say you don't know and suggest contacting an academic advisor.

Rules you MUST follow:
- Be professional, warm, and student-centered.
- Use short bullets for lists (requirements, steps, recommended courses).
- Include page citations by copying the bracket tags from the relevant chunks
  (e.g., [2025-2026 course catalog.pdf, p. 367]).
- Never hallucinate course counts, requirements, or policies.

Course Recommendation Guidance (when applicable):
- Prioritize courses aligned with the student's major/concentration/interests.
- Verify prerequisites before recommending.
- Recommend a balanced load (major/core + gen ed + electives).
- Consider student's year (100-level for first-years, then 200/300 etc.).
- Don't suggest courses already completed or their prerequisites; suggest the next level instead.
- List suggested courses in ascending order (100–500).

QUESTION:
{question}

{f"CONVERSATION HISTORY:\n{history_context}\n" if history_context else ""}
KNOWLEDGE (catalog snippets with page tags):
{knowledge}
"""
        
        # Get response from LLM
        response = self.llm.invoke(rag_prompt)
        answer = response.content
        
        return answer, citations

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
