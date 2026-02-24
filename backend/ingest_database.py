# ingest_database.py
"""
Builds/updates the Chroma vector DB from PDFs in ./data.
- Uses OpenAI embeddings (text-embedding-3-large)
- Preserves PDF metadata (source path + page + doc_type) for later citations
- Larger chunk size (1200/200) to keep course context together
- Classifies documents as 'catalog' or 'policy' based on filename
"""

from uuid import uuid4
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_chroma import Chroma
from google_docs_loader import load_google_docs
import config
import os
import re

load_dotenv()

# Paths & names 
DATA_PATH = config.DATA_PATH
CHROMA_PATH = config.CHROMA_PATH
COLLECTION = config.CHROMA_COLLECTION_NAME

# Embeddings
# Requires OPENAI_API_KEY in environment
embeddings_model = OpenAIEmbeddings(model=config.EMBEDDING_MODEL)

def classify_document_type(filename: str) -> str:
    """
    Classify a document as 'catalog' or 'policy' based on filename.

    Args:
        filename: The base filename (not full path)

    Returns:
        'catalog' or 'policy'
    """
    # Check against explicit mappings in config
    for doc_type, filenames in config.DOCUMENT_TYPE_MAPPINGS.items():
        if filename in filenames:
            return doc_type

    # Fallback heuristics if not in explicit mappings
    filename_lower = filename.lower()
    if "catalog" in filename_lower or "course catalog" in filename_lower:
        return "catalog"
    elif "policy" in filename.upper() or "POLICY" in filename:
        return "policy"

    # Default to policy if uncertain (safer to be more restrictive)
    print(f"[WARNING] Could not classify '{filename}', defaulting to 'policy'")
    return "policy"

COURSE_START_RE = re.compile(r'(?m)^(?P<code>[A-Z]{2,4}\\s?\\d{3}[A-Z]?)\\s*[:\\.-]\\s+')
PAGE_MARKER_RE = re.compile(r'\\[\\[PAGE:(\\d+)\\]\\]')

SECTION_PATTERNS = {
    "freeman_core": [
        "freeman college core curriculum",
        "freeman college of management core curriculum",
        "freeman college core requirements",
    ],
    "sequence": [
        "recommended sequence",
        "four-year plan",
        "four year plan",
        "first year",
        "sophomore year",
        "junior year",
        "senior year",
    ],
    "major_requirements": [
        "major requirements",
        "business analytics major requirements",
    ],
}

def assign_section_metadata(text: str) -> str:
    """
    Heuristic section tagging to help retrieval for sequence/core/requirements blocks.
    Returns a section label or empty string if no match.
    """
    t = (text or "").lower()
    for section, needles in SECTION_PATTERNS.items():
        if any(n in t for n in needles):
            return section
    return ""

def _get_page_for_offset(text: str, offset: int) -> int:
    """Return 0-based page number for a byte offset in a marker-annotated string."""
    matches = list(PAGE_MARKER_RE.finditer(text, 0, offset))
    if not matches:
        return 0
    return int(matches[-1].group(1))

def extract_course_documents(catalog_docs: list) -> list:
    """
    Extract course-level documents from the catalog so each course entry is its own chunk.
    This reduces course-title/description bleed between adjacent courses.
    """
    if not catalog_docs:
        return []

    catalog_docs_sorted = sorted(catalog_docs, key=lambda d: d.metadata.get("page", 0))
    source_path = catalog_docs_sorted[0].metadata.get("source", "catalog.pdf")

    # Build a single text blob with page markers for citation alignment.
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

        course_docs.append(
            Document(
                page_content=cleaned,
                metadata={
                    "source": source_path,
                    "page": page,
                    "doc_type": "catalog",
                    "course_code": code,
                },
            )
        )

    print(f"Extracted {len(course_docs)} course entries from catalog.")
    return course_docs

#  Load PDFs
# PyPDFDirectoryLoader automatically adds metadata:
#   doc.metadata["source"] == filepath
#   doc.metadata["page"]   == 0-based page number
# Load PDFs - new way 
# loader = PyPDFDirectoryLoader(DATA_PATH)
# raw_documents = loader.load()

# print(f"Loaded {len(raw_documents)} raw pages from {DATA_PATH}")
pdf_documents = []
if not config.GOOGLE_DOCS_ONLY:
    loader = PyPDFDirectoryLoader(DATA_PATH)
    pdf_documents = loader.load()
    # Keep only catalog PDFs; policy docs should come from Google Docs
    filtered_pdfs = []
    for doc in pdf_documents:
        source_path = doc.metadata.get("source", "")
        filename = os.path.basename(source_path)
        if classify_document_type(filename) == "catalog":
            filtered_pdfs.append(doc)
    pdf_documents = filtered_pdfs
    print(f"Loaded {len(pdf_documents)} catalog pages from {DATA_PATH}")

# Load Google Docs (if configured)
google_docs = load_google_docs()
if google_docs:
    print(f"Loaded {len(google_docs)} Google Docs from {config.GOOGLE_DOCS_CSV}")

raw_documents = pdf_documents + google_docs

print(f"Total raw documents: {len(raw_documents)}")

# Add doc_type metadata to each document
doc_type_counts = {"catalog": 0, "policy": 0}
for doc in raw_documents:
    source_path = doc.metadata.get("source", "")
    filename = os.path.basename(source_path)
    existing_type = doc.metadata.get("doc_type")
    doc_type = existing_type or classify_document_type(filename)
    doc.metadata["doc_type"] = doc_type
    doc_type_counts[doc_type] += 1

print(f"Document classification:")
print(f"  - Catalog pages: {doc_type_counts['catalog']}")
print(f"  - Policy pages: {doc_type_counts['policy']}")

# Extract course-level docs from catalog for better precision
catalog_docs = [d for d in raw_documents if d.metadata.get("doc_type") == "catalog"]
course_docs = extract_course_documents(catalog_docs)

#  Split into chunks 
# Larger chunks so course titles, prerequisites, and rules stay together
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1200,
    chunk_overlap=200,
    length_function=len,
    is_separator_regex=False,
)

chunks = text_splitter.split_documents(raw_documents)
print(f"Created {len(chunks)} chunks")

# Tag sections on catalog chunks to improve retrieval for sequence/core curriculum questions
for c in chunks:
    if c.metadata.get("doc_type") == "catalog":
        section = assign_section_metadata(c.page_content)
        if section:
            c.metadata["section"] = section

# Add course-level documents on top of the regular chunks
if course_docs:
    for c in course_docs:
        section = assign_section_metadata(c.page_content)
        if section:
            c.metadata["section"] = section
    chunks.extend(course_docs)
    print(f"Total chunks after adding course entries: {len(chunks)}")

# Verify doc_type is preserved in chunks
chunks_with_type = sum(1 for c in chunks if "doc_type" in c.metadata)
print(f"Chunks with doc_type metadata: {chunks_with_type}/{len(chunks)}")

#  Connect to Chroma (persisted) 
vector_store = Chroma(
    collection_name=COLLECTION,
    embedding_function=embeddings_model,
    persist_directory=CHROMA_PATH,
)

#  Add in batches 
BATCH_SIZE = 200
uuids = [str(uuid4()) for _ in range(len(chunks))]
total = len(chunks)
print(f"Total chunks to upsert: {total}")

for i in range(0, total, BATCH_SIZE):
    j = min(i + BATCH_SIZE, total)
    batch_chunks = chunks[i:j]
    batch_ids = uuids[i:j]
    print(f"Adding batch {i//BATCH_SIZE + 1}: chunks {i+1}-{j}")
    vector_store.add_documents(documents=batch_chunks, ids=batch_ids)

# ChromaDB auto-persists when using persist_directory
print(f"Added {total} chunks to {CHROMA_PATH} (collection='{COLLECTION}').")
print("\n" + "="*60)
print("IMPORTANT: Database ingestion complete!")
print("All documents have been classified and indexed with doc_type metadata.")
print("If you experience issues, delete the chroma_db folder and re-run this script.")
print("="*60)
