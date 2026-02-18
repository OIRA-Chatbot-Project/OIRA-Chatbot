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
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_chroma import Chroma
import config
import os

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

#  Load PDFs
# PyPDFDirectoryLoader automatically adds metadata:
#   doc.metadata["source"] == filepath
#   doc.metadata["page"]   == 0-based page number
loader = PyPDFDirectoryLoader(DATA_PATH)
raw_documents = loader.load()

print(f"Loaded {len(raw_documents)} raw pages from {DATA_PATH}")

# Add doc_type metadata to each document
doc_type_counts = {"catalog": 0, "policy": 0}
for doc in raw_documents:
    source_path = doc.metadata.get("source", "")
    filename = os.path.basename(source_path)
    doc_type = classify_document_type(filename)
    doc.metadata["doc_type"] = doc_type
    doc_type_counts[doc_type] += 1

print(f"Document classification:")
print(f"  - Catalog pages: {doc_type_counts['catalog']}")
print(f"  - Policy pages: {doc_type_counts['policy']}")

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
