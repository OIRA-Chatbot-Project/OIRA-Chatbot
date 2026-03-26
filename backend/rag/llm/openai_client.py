"""OpenAI LLM client wrapper."""
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from core.settings import settings


def get_main_llm() -> ChatOpenAI:
    """Get the main LLM for answer generation."""
    return ChatOpenAI(
        temperature=0.3,
        model=settings.llm.OPENAI_MODEL,
        api_key=settings.llm.OPENAI_API_KEY,
    )


def get_light_llm() -> ChatOpenAI:
    """Get the light LLM for decomposition and conversational responses."""
    return ChatOpenAI(
        temperature=0.1,
        model=settings.llm.OPENAI_LIGHT_MODEL,
        api_key=settings.llm.OPENAI_API_KEY,
    )


def get_classifier_llm() -> ChatOpenAI:
    """Get the classifier LLM."""
    return ChatOpenAI(
        temperature=settings.rag.QUESTION_CLASSIFIER_TEMPERATURE,
        model=settings.llm.OPENAI_LIGHT_MODEL,
        api_key=settings.llm.OPENAI_API_KEY,
    )


def get_embeddings() -> OpenAIEmbeddings:
    """Get the embeddings model."""
    return OpenAIEmbeddings(model=settings.llm.EMBEDDING_MODEL)
