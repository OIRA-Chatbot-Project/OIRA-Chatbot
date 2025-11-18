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

# ChromaDB Configuration
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "bucknell_catalogue")

# API Configuration
API_VERSION = "1.0.0"
API_TITLE = "OIRA Chatbot API"
API_DESCRIPTION = "API for Bucknell University course catalog chatbot"

# CORS Configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")
