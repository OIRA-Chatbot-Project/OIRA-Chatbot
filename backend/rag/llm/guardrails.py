"""Answer cleaning and post-processing guardrails."""
import re


def clean_answer(answer: str) -> str:
    """Remove inline bracket citations and normalize spacing."""
    try:
        cleaned = re.sub(r"\[[^\]]+?,\s*p\.\s*\d+\]", "", answer)
        cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = re.sub(r"(?<=\S)[ \t]{2,}", " ", cleaned)
        return cleaned.strip()
    except Exception:
        return answer
