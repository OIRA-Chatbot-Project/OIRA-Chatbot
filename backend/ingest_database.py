# ingest_database.py
"""
Builds/updates the Chroma vector DB from PDFs in ./data.
- Uses OpenAI embeddings (text-embedding-3-large)
- Preserves PDF metadata (source path + page) for later citations
- Larger chunk size (1200/200) to keep course context together
"""

from uuid import uuid4
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_chroma import Chroma
import config

load_dotenv()

# Paths & names 
DATA_PATH = config.DATA_PATH
CHROMA_PATH = config.CHROMA_PATH
COLLECTION = config.CHROMA_COLLECTION_NAME

# Embeddings 
# Requires OPENAI_API_KEY in environment
embeddings_model = OpenAIEmbeddings(model=config.EMBEDDING_MODEL)

#  Load PDFs 
# PyPDFDirectoryLoader automatically adds metadata:
#   doc.metadata["source"] == filepath
#   doc.metadata["page"]   == 0-based page number
loader = PyPDFDirectoryLoader(DATA_PATH)
raw_documents = loader.load()

print(f"Loaded {len(raw_documents)} raw pages from {DATA_PATH}")

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
print("Tip: If you change PDFs significantly, consider deleting the chroma_db folder and re-ingesting.")
