"""Chroma vector store adapter."""
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from core.settings import settings


def get_chroma_store(chroma_path: str = None, collection_name: str = None) -> Chroma:
    """Get a Chroma vector store instance."""
    embeddings_model = OpenAIEmbeddings(model=settings.llm.EMBEDDING_MODEL)
    return Chroma(
        collection_name=collection_name or settings.vector.CHROMA_COLLECTION_NAME,
        embedding_function=embeddings_model,
        persist_directory=chroma_path or settings.vector.CHROMA_PATH,
    )
