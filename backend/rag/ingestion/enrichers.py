"""Metadata enrichers for RAG ingestion."""
import re
from langchain_core.documents import Document
from rag.constants import COURSE_START_RE, PAGE_MARKER_RE, SECTION_PATTERNS


def assign_section_metadata(text: str) -> str:
    """Heuristic section tagging."""
    t = (text or "").lower()
    for section, needles in SECTION_PATTERNS.items():
        if any(n in t for n in needles):
            return section
    return ""


def _get_page_for_offset(text: str, offset: int) -> int:
    """Return 0-based page number for a byte offset."""
    matches = list(PAGE_MARKER_RE.finditer(text, 0, offset))
    if not matches:
        return 0
    return int(matches[-1].group(1))


def extract_course_documents(catalog_docs: list) -> list:
    """Extract course-level documents from the catalog."""
    if not catalog_docs:
        return []
    catalog_docs_sorted = sorted(catalog_docs, key=lambda d: d.metadata.get("page", 0))
    source_path = catalog_docs_sorted[0].metadata.get("source", "catalog.pdf")
    parts = []
    for d in catalog_docs_sorted:
        page = d.metadata.get("page", 0)
        parts.append(f"\n[[PAGE:{page}]]\n{d.page_content}\n")
    catalog_text = "\n".join(parts)
    matches = list(COURSE_START_RE.finditer(catalog_text))
    if not matches:
        print("[WARNING] No course entries detected in catalog.")
        return []
    course_docs = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(catalog_text)
        chunk = catalog_text[start:end]
        page = _get_page_for_offset(catalog_text, start)
        code = m.group("code").replace("  ", " ").strip()
        cleaned = PAGE_MARKER_RE.sub("", chunk).strip()
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        if len(cleaned) < 40:
            continue
        course_docs.append(Document(
            page_content=cleaned,
            metadata={"source": source_path, "page": page, "doc_type": "catalog", "course_code": code},
        ))
    print(f"Extracted {len(course_docs)} course entries from catalog.")
    return course_docs
