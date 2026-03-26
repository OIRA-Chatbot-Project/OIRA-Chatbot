"""
Backward-compatible shim - imports from core.settings.
"""
from core.settings import settings

DATA_PATH = settings.ingestion.DATA_PATH
CHROMA_PATH = settings.vector.CHROMA_PATH
DATABASE_URL = settings.db.DATABASE_URL
GOOGLE_DOCS_CSV = settings.ingestion.GOOGLE_DOCS_CSV
GOOGLE_DOCS_CACHE_DIR = settings.ingestion.GOOGLE_DOCS_CACHE_DIR
GOOGLE_DOCS_REFRESH = settings.ingestion.GOOGLE_DOCS_REFRESH
GOOGLE_DOCS_ONLY = settings.ingestion.GOOGLE_DOCS_ONLY
OPENAI_API_KEY = settings.llm.OPENAI_API_KEY
OPENAI_MODEL = settings.llm.OPENAI_MODEL
OPENAI_LIGHT_MODEL = settings.llm.OPENAI_LIGHT_MODEL
OPENAI_TEMPERATURE = settings.llm.OPENAI_TEMPERATURE
EMBEDDING_MODEL = settings.llm.EMBEDDING_MODEL
NUM_RETRIEVAL_RESULTS = settings.rag.NUM_RETRIEVAL_RESULTS
CHUNK_SIZE = settings.rag.CHUNK_SIZE
CHUNK_OVERLAP = settings.rag.CHUNK_OVERLAP
USE_MULTI_STEP_QUERY = settings.rag.USE_MULTI_STEP_QUERY
RETRIEVER_K = settings.rag.RETRIEVER_K
RETRIEVER_FETCH_K = settings.rag.RETRIEVER_FETCH_K
RETRIEVER_LAMBDA_MULT = settings.rag.RETRIEVER_LAMBDA_MULT
MAX_MULTI_STEP_DOCS = settings.rag.MAX_MULTI_STEP_DOCS
MIN_DOCS_PER_SUBQUERY = settings.rag.MIN_DOCS_PER_SUBQUERY
SIMPLE_QUERY_MAX_WORDS = settings.rag.SIMPLE_QUERY_MAX_WORDS
CHROMA_COLLECTION_NAME = settings.vector.CHROMA_COLLECTION_NAME
API_VERSION = settings.app.API_VERSION
API_TITLE = settings.app.API_TITLE
API_DESCRIPTION = settings.app.API_DESCRIPTION
ALLOWED_ORIGINS = settings.app.ALLOWED_ORIGINS
QUESTION_CLASSIFIER_TEMPERATURE = settings.rag.QUESTION_CLASSIFIER_TEMPERATURE
ENABLE_OFF_TOPIC_DETECTION = settings.rag.ENABLE_OFF_TOPIC_DETECTION
SUMMARY_WINDOW_SIZE = settings.rag.SUMMARY_WINDOW_SIZE
ENABLE_CONVERSATION_MEMORY = settings.rag.ENABLE_CONVERSATION_MEMORY

DOCUMENT_TYPE_MAPPINGS = {
    "catalog": [
        "2025-2026 course catalog.pdf",
        "datalab-output-2025-2026 course catalog.pdf.md",
    ],
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
        "WITHDRAWAL, LEAVE OF ABSENCE & SUSPENSION POLICY.pdf",
    ],
}

OFF_TOPIC_MESSAGE = "That one's a bit outside what I cover — I'm set up specifically to help with Bucknell course information and academic policies (things like course requirements, prerequisites, registration, grading, and degree requirements). Feel free to ask me anything in those areas!"
GREETING_MESSAGE = "Hey there! I'm the Bucknell academic assistant. I can help you with course information (descriptions, prerequisites, credits, recommendations), major and minor requirements, and academic policies (registration, grading, withdrawal, and more). What would you like to know?"
GREETING_SHORT_MESSAGE = "Hi again! What can I help you with?"
THANK_YOU_MESSAGE = "You're welcome! Let me know if you have any other questions about courses, majors, or academic policies."
CLARIFICATION_MESSAGE = "I'm happy to help! Could you tell me a little more about what you're looking for? You can ask about:\n\n- Courses (e.g., \"What are the prerequisites for ECON 103?\")\n- Majors and minors (e.g., \"What courses do I need for a CS major?\")\n- Academic policies (e.g., \"What's the withdrawal policy?\")"
POLICY_DISCLAIMER = """

---
**Important Note:** This information is from official Bucknell official documents, but they may change over time. For official guidance and questions about how these policies apply to your specific situation, please consult with your academic advisor or the Office of the Registrar."""
