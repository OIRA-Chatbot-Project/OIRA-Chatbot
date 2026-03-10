"""
Prompt templates and functions for the OIRA chatbot.

Templates are loaded from .md files in this directory at import time.
Public API is unchanged from the original prompts.py module:
- SYSTEM_PROMPT: Main system instructions for the chatbot
- get_decompose_prompt(): Query decomposition for multi-step reasoning
- get_user_prompt(): RAG user message construction
- get_contextualize_prompt(): Conversation history integration
- get_question_classifier_prompt(): Question type classification
"""
from pathlib import Path
from string import Template

_DIR = Path(__file__).parent


def _load(filename: str) -> str:
    """Load a prompt template from the prompts directory."""
    return (_DIR / filename).read_text(encoding="utf-8").strip()


# Load all templates once at import time
SYSTEM_PROMPT: str = _load("system.md")

_DECOMPOSE_TPL = Template(_load("decompose.md"))
_CONTEXTUALIZE_TPL = Template(_load("contextualize.md"))
_CLASSIFIER_TPL = Template(_load("question_classifier.md"))


def get_decompose_prompt(question: str) -> str:
    """
    Generate prompt for query decomposition into sub-questions.

    Used for multi-step reasoning to handle complex queries like comparisons,
    multi-part questions, or queries requiring multiple pieces of information.

    Args:
        question: The user's original question

    Returns:
        Prompt string that instructs the LLM to return structured JSON with
        query type and optional sub-questions
    """
    return _DECOMPOSE_TPL.substitute(question=question)


def get_user_prompt(question: str, knowledge: str, history_context: str) -> str:
    """
    Build the user message for RAG generation.

    Combines the user's question with retrieved knowledge and conversation history
    to create a complete prompt for answer generation.

    Args:
        question: The user's current question
        knowledge: Retrieved context from the vector store (with citations)
        history_context: Formatted conversation history (empty string if none)

    Returns:
        Formatted user prompt string with all context
    """
    prompt_parts = []

    # Add knowledge section (always present)
    prompt_parts.append(f"KNOWLEDGE:\n{knowledge}\n")

    # Add conversation history if available
    if history_context:
        prompt_parts.append(f"CONVERSATION HISTORY:\n{history_context}\n")

    # Add the user's question
    prompt_parts.append(
        f"QUESTION:\n{question}\n\n"
        "Please answer the question using ONLY the database in the knowledge base above. "
        "You must include citations in the format [Source, p. X] for all factual claims. "
        "Follow the system instructions carefully regarding formatting, hallucination prevention, "
        "and fallback responses."
    )

    return "\n".join(prompt_parts)


def get_contextualize_prompt(question: str, history_text: str) -> str:
    """
    Generate prompt to rewrite a question with conversation context.

    Handles follow-up questions by incorporating conversation history to create
    a standalone query suitable for retrieval.

    Args:
        question: The current user question (may reference previous context)
        history_text: Formatted conversation history

    Returns:
        Prompt instructing the LLM to rewrite the question as standalone
    """
    return _CONTEXTUALIZE_TPL.substitute(question=question, history_text=history_text)


def get_question_classifier_prompt(question: str) -> str:
    """
    Generate prompt for classifying question type before retrieval.

    Determines whether a question is about:
    - course_catalog: Course information, descriptions, prerequisites
    - academic_policy: Academic policies, rules, procedures
    - off_topic: Non-academic questions that should be rejected

    Args:
        question: The user's question

    Returns:
        Prompt string instructing the LLM to return JSON with classification
    """
    return _CLASSIFIER_TPL.substitute(question=question)
