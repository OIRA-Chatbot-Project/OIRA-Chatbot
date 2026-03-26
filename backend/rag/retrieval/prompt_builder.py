"""Prompt building from retrieved documents."""
import os
import re
from typing import List, Dict, Optional, Any


def short_source(path: str) -> str:
    """Turn a long file path into a friendly filename."""
    if not path:
        return "Source"
    name = os.path.basename(path)
    return name.replace("_", " ")


def prepare_knowledge(docs: List) -> str:
    """Build a labeled context string so the model can cite pages."""
    parts = []
    for d in docs:
        meta = d.metadata or {}
        src = short_source(meta.get("source", "Catalogue"))
        page = (meta.get("page", 0) or 0) + 1
        header = f"[{src}, p. {page}]"
        content = normalize_text(d.page_content).strip()
        parts.append(f"{header}\n{content}\n{header}\n")
    return "\n".join(parts)


def normalize_text(text: str) -> str:
    """Normalize spacing artifacts from PDF extraction."""
    if not text:
        return text
    return re.sub(r"\s+([,.;:!?])", r"\1", text)


def format_history_context(conversation_history: List[Dict[str, str]]) -> str:
    """Format conversation history for inclusion in prompt."""
    if not conversation_history:
        return ""
    return "\n".join([
        f"{msg['role'].capitalize()}: {msg['content'][:300]}"
        for msg in conversation_history[-6:]
    ])


def build_citations(docs: List, get_document_url_fn) -> List[Dict[str, Any]]:
    """Build citations list from retrieved docs."""
    citations = []
    for doc in docs:
        meta = doc.metadata or {}
        src = short_source(meta.get("source", "Catalogue"))
        page = (meta.get("page", 0) or 0) + 1
        source_filename = os.path.basename(meta.get("source", "catalog.pdf"))
        doc_type = meta.get("doc_type", "catalog")
        source_url = meta.get("source_url")
        if doc_type == "policy" and not source_url:
            continue
        citation = {
            "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
            "source": src,
            "page": page,
            "url": get_document_url_fn(source_filename, page, source_url, doc_type),
            "doc_type": doc_type,
            "filename": source_filename,
        }
        citations.append(citation)
    return citations
