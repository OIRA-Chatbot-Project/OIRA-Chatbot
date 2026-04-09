"""
Configuration settings for the OIRA Chatbot API.

This module loads environment variables and defines constants used throughout the application,
including database URLs, OpenAI API keys, RAG configuration, and other application settings.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Paths
DATA_PATH = os.getenv("DATA_PATH", "data")
CHROMA_PATH = os.getenv("CHROMA_PATH", "chroma_db")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./chatbot.db")

# Google Docs ingestion
GOOGLE_DOCS_CSV = os.getenv("GOOGLE_DOCS_CSV", "data/google_docs.csv")
GOOGLE_DOCS_CACHE_DIR = os.getenv("GOOGLE_DOCS_CACHE_DIR", "data/google_docs_cache")
GOOGLE_DOCS_REFRESH = os.getenv("GOOGLE_DOCS_REFRESH", "false").lower() == "true"
GOOGLE_DOCS_ONLY = os.getenv("GOOGLE_DOCS_ONLY", "false").lower() == "true"

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_LIGHT_MODEL = os.getenv("OPENAI_LIGHT_MODEL", "gpt-4.1-nano")
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.5"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")

# RAG Configuration
NUM_RETRIEVAL_RESULTS = int(os.getenv("NUM_RETRIEVAL_RESULTS", "5"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "300"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))
USE_MULTI_STEP_QUERY = os.getenv("USE_MULTI_STEP_QUERY", "true").lower() == "true"

# Retriever Configuration
RETRIEVER_K = int(os.getenv("RETRIEVER_K", "12"))  # Number of documents to retrieve
RETRIEVER_FETCH_K = int(os.getenv("RETRIEVER_FETCH_K", "80"))  # Candidates for MMR
RETRIEVER_LAMBDA_MULT = float(os.getenv("RETRIEVER_LAMBDA_MULT", "0.4"))  # MMR diversity (0=diverse, 1=similar)
MAX_MULTI_STEP_DOCS = int(os.getenv("MAX_MULTI_STEP_DOCS", "30"))  # Max docs for multi-step queries
MIN_DOCS_PER_SUBQUERY = int(os.getenv("MIN_DOCS_PER_SUBQUERY", "4"))  # Minimum docs per sub-question
SIMPLE_QUERY_MAX_WORDS = int(os.getenv("SIMPLE_QUERY_MAX_WORDS", "15"))  # Max words for simple query heuristic

# ChromaDB Configuration
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "bucknell_catalogue")

# API Configuration
API_VERSION = "1.0.0"
API_TITLE = "OIRA Chatbot API"
API_DESCRIPTION = "API for Bucknell University course catalog chatbot"

# CORS Configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")

# Question Classification Configuration
QUESTION_CLASSIFIER_TEMPERATURE = float(os.getenv("QUESTION_CLASSIFIER_TEMPERATURE", "0.1"))
ENABLE_OFF_TOPIC_DETECTION = os.getenv("ENABLE_OFF_TOPIC_DETECTION", "true").lower() == "true"

# Conversation Memory Configuration
SUMMARY_WINDOW_SIZE = int(os.getenv("SUMMARY_WINDOW_SIZE", "6"))  # messages kept verbatim
ENABLE_CONVERSATION_MEMORY = os.getenv("ENABLE_CONVERSATION_MEMORY", "true").lower() == "true"

# Document Type Configuration
DOCUMENT_TYPE_MAPPINGS = {
    # Catalog documents
    # Note: markdown versions (datalab-output-*.md) are loaded preferentially over
    # their PDF counterparts and have doc_type set explicitly at load time.
    "catalog": [
        "2025-2026 course catalog.pdf",
        "datalab-output-2025-2026 course catalog.pdf.md",
    ],
    # Policy documents
    "policy": [
        "ACADEMIC RESPONSIBILITY POLICY.pdf",
        "ACADEMIC STANDING.pdf",
        "ADVANCED PLACEMENT & CREDIT POLICY.pdf",
        "CLASS ATTENDANCE POLICY.pdf",
        "COLLEGE LEVEL EXAMINATION PROGRAM (CLEP) POLICY.pdf",
        "COURSE REGISTRATION & WITHDRAWAL POLICY.pdf",
        "CREDIT BY EXAMINATION POLICY.pdf",
        "DECLARATION OF A MINOR POLICY.pdf",
        "DEGREE & GRADUATION REQUIREMENTS POLICY.pdf",
        "DOUBLE COUNTING COURSES POLICY.pdf",
        "GRADE APPEALS POLICY.pdf",
        "GRADE REPLACEMENT POLICY.pdf",
        "INCOMPLETE GRADES POLICY.pdf",
        "INTERNATIONAL BACCALAUREATE (IB) & CAMBRIDGE INTERNATIONAL A LEVEL CREDIT POLICY.pdf",
        "SUPERIOR ACADEMIC ACHIEVEMENT (Honors Designations) POLICY.pdf",
        "TRANSFER OF ACADEMIC CREDIT.pdf",
        "WITHDRAWAL, LEAVE OF ABSENCE & SUSPENSION POLICY.pdf"
    ]
}

# Off-Topic Rejection Message
OFF_TOPIC_MESSAGE = "That one's a bit outside what I cover — I'm set up specifically to help with Bucknell course information and academic policies (things like course requirements, prerequisites, registration, grading, and degree requirements). Feel free to ask me anything in those areas!"

# Conversational Response Messages
GREETING_MESSAGE = "Hey there! I'm the Bucknell academic assistant. I can help you with course information (descriptions, prerequisites, credits, recommendations), major and minor requirements, and academic policies (registration, grading, withdrawal, and more). What would you like to know?"

GREETING_SHORT_MESSAGE = "Hi again! What can I help you with?"

THANK_YOU_MESSAGE = "You're welcome! Let me know if you have any other questions about courses, majors, or academic policies."

CLARIFICATION_MESSAGE = "I'm happy to help! Could you tell me a little more about what you're looking for? You can ask about:\n\n- Courses (e.g., \"What are the prerequisites for ECON 103?\")\n- Majors and minors (e.g., \"What courses do I need for a CS major?\")\n- Academic policies (e.g., \"What's the withdrawal policy?\")"

# Policy Response Disclaimer
POLICY_DISCLAIMER = """

---
**Important Note:** This information is from official Bucknell official documents, but they may change over time. For official guidance and questions about how these policies apply to your specific situation, please consult with your academic advisor or the Office of the Registrar."""
