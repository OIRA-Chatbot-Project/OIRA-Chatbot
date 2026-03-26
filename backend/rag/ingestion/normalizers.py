"""Text normalization utilities."""
import re


def normalize_text(text: str) -> str:
    """Normalize spacing artifacts from PDF extraction."""
    if not text:
        return text
    return re.sub(r"\s+([,.;:!?])", r"\1", text)


def normalize_markdown(text: str) -> str:
    """Normalize generated Markdown text."""
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()
