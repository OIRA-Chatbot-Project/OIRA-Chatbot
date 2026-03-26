"""Document type classification."""
from rag.constants import DOCUMENT_TYPE_MAPPINGS


def classify_document_type(filename: str) -> str:
    """Classify a document as 'catalog' or 'policy' based on filename."""
    for doc_type, filenames in DOCUMENT_TYPE_MAPPINGS.items():
        if filename in filenames:
            return doc_type
    filename_lower = filename.lower()
    if "catalog" in filename_lower or "course catalog" in filename_lower:
        return "catalog"
    elif "policy" in filename.upper() or "POLICY" in filename:
        return "policy"
    print(f"[WARNING] Could not classify '{filename}', defaulting to 'policy'")
    return "policy"
