"""
Prompt templates and functions for the OIRA chatbot.

Templates are loaded from .md files in this directory at import time.
Public API:
- SYSTEM_PROMPT: Fallback system instructions (used when category is unrecognised)
- CATALOG_SYSTEM_PROMPT: System prompt tailored for course_catalog questions
- POLICY_SYSTEM_PROMPT: System prompt tailored for academic_policy questions
- CONVERSATIONAL_SYSTEM_PROMPT: System prompt for conversational (non-RAG) replies
- get_decompose_prompt(): Query decomposition for multi-step reasoning
- get_user_prompt(): RAG user message construction (supports summary + user_profile)
- get_contextualize_prompt(): Conversation history integration
- get_question_classifier_prompt(): Question type classification
- get_conversational_prompt(): User-turn prompt for greeting/thanks/clarification/off_topic
"""
from pathlib import Path
from string import Template
from typing import Optional, Dict

_DIR = Path(__file__).parent


def _load(filename: str) -> str:
    """Load a prompt template from the prompts directory."""
    return (_DIR / filename).read_text(encoding="utf-8").strip()


# Load all templates once at import time
SYSTEM_PROMPT: str = _load("system.md")
CATALOG_SYSTEM_PROMPT: str = _load("system_catalog.md")
POLICY_SYSTEM_PROMPT: str = _load("system_policy.md")

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


def get_user_prompt(
    question: str,
    knowledge: str,
    history_context: str,
    summary: Optional[str] = None,
    user_profile: Optional[Dict[str, str]] = None,
) -> str:
    """
    Build the user message for RAG generation.

    Combines the user's question with retrieved knowledge, conversation history,
    an optional session summary, and an optional persistent user profile.

    Section injection order (top → bottom):
    1. USER CONTEXT — if user_profile is non-empty
    2. CONVERSATION SUMMARY — if summary is non-empty
    3. CONVERSATION HISTORY — verbatim last-N messages
    4. KNOWLEDGE — retrieved documents
    5. QUESTION + instructions

    Args:
        question: The user's current question
        knowledge: Retrieved context from the vector store (with citations)
        history_context: Formatted conversation history (empty string if none)
        summary: Optional paragraph summarising older messages no longer in the verbatim window
        user_profile: Optional dict of persistent facts about the user (major, year, etc.)

    Returns:
        Formatted user prompt string with all context
    """
    prompt_parts = []

    # 1. USER CONTEXT block
    if user_profile:
        user_type = user_profile.get("user_type", "unknown")
        if user_type == "student":
            header_label = "this student"
        elif user_type in ("faculty", "advisor", "staff"):
            header_label = "this user"
        else:
            header_label = "this user"

        facts_lines = "\n".join(f"{k}: {v}" for k, v in user_profile.items())
        prompt_parts.append(
            f"USER CONTEXT:\n"
            f"The following facts about {header_label} are known from prior conversations.\n"
            f"Use them to personalize your answer, but do NOT treat them as confirmed "
            f"unless the user restates them in this session.\n"
            f"{facts_lines}\n"
        )

    # 2. CONVERSATION SUMMARY block
    if summary:
        prompt_parts.append(
            f"CONVERSATION SUMMARY:\n"
            f"The following is a summary of earlier messages in this session no longer in the "
            f"verbatim history window. Use it for additional context but prioritize the "
            f"verbatim CONVERSATION HISTORY for recent specifics.\n"
            f"{summary}\n"
        )

    # 3. CONVERSATION HISTORY block
    if history_context:
        prompt_parts.append(f"CONVERSATION HISTORY:\n{history_context}\n")

    # 4. KNOWLEDGE block (always present)
    prompt_parts.append(f"KNOWLEDGE:\n{knowledge}\n")

    # 5. QUESTION + instructions
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


def get_question_classifier_prompt(question: str, history_text: str = "") -> str:
    """
    Generate prompt for classifying question type before retrieval.

    Determines whether a question is about:
    - course_catalog: Course information, descriptions, prerequisites
    - academic_policy: Academic policies, rules, procedures
    - off_topic: Non-academic questions that should be rejected

    Args:
        question: The user's question
        history_text: Optional formatted conversation history for follow-up context.

    Returns:
        Prompt string instructing the LLM to return JSON with classification
    """
    history_section = (
        f"CONVERSATION HISTORY (last few turns):\n{history_text}\n"
        if history_text
        else ""
    )
    return _CLASSIFIER_TPL.substitute(question=question, history_section=history_section)


CONVERSATIONAL_SYSTEM_PROMPT: str = (
    "You are a friendly, warm academic assistant for Bucknell University. "
    "You help students with course information, major requirements, and academic policies. "
    "Be natural and conversational. Keep responses concise (2-4 sentences max). "
    "Do not use bullet points or headers for casual exchanges."
)


def _parse_conversational_templates() -> dict[str, Template]:
    """Parse conversational.md into a dict keyed by category name."""
    raw = _load("conversational.md")
    blocks = [b.strip() for b in raw.split("---") if b.strip()]
    templates: dict[str, Template] = {}
    for block in blocks:
        lines = block.splitlines()
        if lines:
            category = lines[0].strip()
            body = "\n".join(lines[1:]).strip()
            templates[category] = Template(body)
    return templates


_CONVERSATIONAL_TPLS = _parse_conversational_templates()


def get_conversational_prompt(category: str, question: str) -> str:
    """Return the user-turn prompt for a conversational category.

    Args:
        category: One of greeting, thank_you, clarification_needed, off_topic.
        question: The student's original message.

    Returns:
        Formatted prompt string.
    """
    tpl = _CONVERSATIONAL_TPLS.get(category, _CONVERSATIONAL_TPLS.get("clarification_needed"))
    if tpl is None:
        return f"Student message: {question}"
    return tpl.substitute(question=question)
