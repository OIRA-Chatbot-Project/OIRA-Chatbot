import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Paths
DATA_PATH = os.getenv("DATA_PATH", "data")
CHROMA_PATH = os.getenv("CHROMA_PATH", "chroma_db")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./chatbot.db")

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.5"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")

# RAG Configuration
NUM_RETRIEVAL_RESULTS = int(os.getenv("NUM_RETRIEVAL_RESULTS", "5"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "300"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))
USE_MULTI_STEP_QUERY = os.getenv("USE_MULTI_STEP_QUERY", "true").lower() == "true"

# Retriever Configuration
RETRIEVER_K = int(os.getenv("RETRIEVER_K", "8"))  # Number of documents to retrieve
RETRIEVER_FETCH_K = int(os.getenv("RETRIEVER_FETCH_K", "50"))  # Candidates for MMR
RETRIEVER_LAMBDA_MULT = float(os.getenv("RETRIEVER_LAMBDA_MULT", "0.4"))  # MMR diversity (0=diverse, 1=similar)
MAX_MULTI_STEP_DOCS = int(os.getenv("MAX_MULTI_STEP_DOCS", "20"))  # Max docs for multi-step queries
MIN_DOCS_PER_SUBQUERY = int(os.getenv("MIN_DOCS_PER_SUBQUERY", "3"))  # Minimum docs per sub-question

# ChromaDB Configuration
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "bucknell_catalogue")

# API Configuration
API_VERSION = "1.0.0"
API_TITLE = "OIRA Chatbot API"
API_DESCRIPTION = "API for Bucknell University course catalog chatbot"

# CORS Configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")
