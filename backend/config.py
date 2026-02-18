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
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")  # Optimized for speed

# RAG Configuration
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "300"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))
USE_MULTI_STEP_QUERY = os.getenv("USE_MULTI_STEP_QUERY", "true").lower() == "true"

# Retriever Configuration (Optimized for performance)
RETRIEVER_K = int(os.getenv("RETRIEVER_K", "8"))  # Number of documents to retrieve (reduced from 12)
RETRIEVER_FETCH_K = int(os.getenv("RETRIEVER_FETCH_K", "40"))  # Candidates for MMR (reduced from 80)
RETRIEVER_LAMBDA_MULT = float(os.getenv("RETRIEVER_LAMBDA_MULT", "0.4"))  # MMR diversity (0=diverse, 1=similar)
MAX_MULTI_STEP_DOCS = int(os.getenv("MAX_MULTI_STEP_DOCS", "20"))  # Max docs for multi-step queries (reduced from 30)
MIN_DOCS_PER_SUBQUERY = int(os.getenv("MIN_DOCS_PER_SUBQUERY", "3"))  # Minimum docs per sub-question (reduced from 4)

# ChromaDB Configuration
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "bucknell_catalogue")

# API Configuration
API_VERSION = "1.0.0"
API_TITLE = "OIRA Chatbot API"
API_DESCRIPTION = "API for Bucknell University course catalog chatbot"

# CORS Configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")

# PDF Base URL Configuration
PDF_BASE_URL = os.getenv("PDF_BASE_URL", "http://localhost:3000")

# Question Classification Configuration
QUESTION_CLASSIFIER_TEMPERATURE = float(os.getenv("QUESTION_CLASSIFIER_TEMPERATURE", "0.1"))
ENABLE_OFF_TOPIC_DETECTION = os.getenv("ENABLE_OFF_TOPIC_DETECTION", "true").lower() == "true"

# Document Type Configuration
DOCUMENT_TYPE_MAPPINGS = {
    # Catalog documents
    "catalog": [
        "2025-2026 course catalog.pdf"
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
OFF_TOPIC_MESSAGE = """I'm a specialized chatbot designed to help with Bucknell University academic questions only.

I can assist with:
- Course information (descriptions, prerequisites, credits)
- Major and minor requirements
- Academic policies (registration, grading, withdrawal, etc.)
- General education requirements
- Course recommendations

I cannot help with:
- Non-academic topics (weather, news, general knowledge)
- Technical support or IT issues
- Housing, dining, or campus facilities
- Financial aid or billing questions
- Social events or student organizations

For non-academic questions, please visit:
- IT Support: https://bucknell.edu/about/offices-services/library-information-technology
- Student Affairs: https://bucknell.edu/life-bucknell/student-affairs

Please feel free to ask me any academic-related questions!"""

# Policy Response Disclaimer
POLICY_DISCLAIMER = """

---
**Important Note:** This information is from official Bucknell academic policies, but policies may change. For official guidance and questions about how these policies apply to your specific situation, please consult with your academic advisor or the Office of the Registrar."""
