"""
Application settings using Pydantic BaseSettings.
Settings are grouped by concern and loaded from environment variables.
"""
from __future__ import annotations
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    API_VERSION: str = "1.0.0"
    API_TITLE: str = "OIRA Chatbot API"
    API_DESCRIPTION: str = "API for Bucknell University course catalog chatbot"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    DEBUG: bool = False

    model_config = {"env_file": ".env", "extra": "ignore"}

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


class DBSettings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./chatbot.db"
    model_config = {"env_file": ".env", "extra": "ignore"}


class LLMSettings(BaseSettings):
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4.1-mini"
    OPENAI_LIGHT_MODEL: str = "gpt-4.1-nano"
    OPENAI_TEMPERATURE: float = 0.5
    EMBEDDING_MODEL: str = "text-embedding-3-large"
    model_config = {"env_file": ".env", "extra": "ignore"}


class VectorSettings(BaseSettings):
    CHROMA_PATH: str = "chroma_db"
    CHROMA_COLLECTION_NAME: str = "bucknell_catalogue"
    model_config = {"env_file": ".env", "extra": "ignore"}


class RAGTuning(BaseSettings):
    NUM_RETRIEVAL_RESULTS: int = 5
    CHUNK_SIZE: int = 300
    CHUNK_OVERLAP: int = 100
    USE_MULTI_STEP_QUERY: bool = True
    RETRIEVER_K: int = 12
    RETRIEVER_FETCH_K: int = 80
    RETRIEVER_LAMBDA_MULT: float = 0.4
    MAX_MULTI_STEP_DOCS: int = 30
    MIN_DOCS_PER_SUBQUERY: int = 4
    SIMPLE_QUERY_MAX_WORDS: int = 15
    QUESTION_CLASSIFIER_TEMPERATURE: float = 0.1
    ENABLE_OFF_TOPIC_DETECTION: bool = True
    SUMMARY_WINDOW_SIZE: int = 6
    ENABLE_CONVERSATION_MEMORY: bool = True
    model_config = {"env_file": ".env", "extra": "ignore"}


class IngestionSettings(BaseSettings):
    DATA_PATH: str = "data"
    GOOGLE_DOCS_CSV: str = "data/google_docs.csv"
    GOOGLE_DOCS_CACHE_DIR: str = "data/google_docs_cache"
    GOOGLE_DOCS_REFRESH: bool = False
    GOOGLE_DOCS_ONLY: bool = False
    model_config = {"env_file": ".env", "extra": "ignore"}


class Settings:
    """Aggregated settings container."""
    def __init__(self):
        self.app = AppSettings()
        self.db = DBSettings()
        self.llm = LLMSettings()
        self.vector = VectorSettings()
        self.rag = RAGTuning()
        self.ingestion = IngestionSettings()


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


settings = get_settings()
