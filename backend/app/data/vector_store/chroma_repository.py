"""
ChromaDB repository — owns vector store initialization and retrieval.

Extracted from ChatbotService.__init__ so the vector store is a proper
data-layer concern injectable into RagPipeline.
"""
from typing import List, Optional
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

from app.core import config


class ChromaRepository:
    """Wraps Chroma vector store and MMR retriever.

    Constructed once per process (via lru_cache in deps.py) and injected
    into RagPipeline as a constructor dependency.
    """

    def __init__(
        self,
        collection_name: str,
        persist_directory: str,
        embedding_model: str,
    ) -> None:
        self.embeddings = OpenAIEmbeddings(model=embedding_model)
        self.store = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=persist_directory,
        )
        self.retriever = self.store.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": config.RETRIEVER_K,
                "fetch_k": config.RETRIEVER_FETCH_K,
                "lambda_mult": config.RETRIEVER_LAMBDA_MULT,
            },
        )

    def mmr_search(self, query: str) -> List:
        """Run MMR retrieval and return LangChain Document objects."""
        return self.retriever.invoke(query)

    def similarity_search(
        self,
        query: str,
        k: int,
        filter: Optional[dict] = None,
    ) -> List:
        """Direct similarity search (non-MMR) with optional metadata filter."""
        kwargs = {"k": k}
        if filter:
            kwargs["filter"] = filter
        return self.store.similarity_search(query, **kwargs)

    def max_marginal_relevance_search(
        self,
        query: str,
        k: int,
        fetch_k: int,
        lambda_mult: float,
        filter: Optional[dict] = None,
    ) -> List:
        """Explicit MMR search with configurable parameters."""
        kwargs = {"k": k, "fetch_k": fetch_k, "lambda_mult": lambda_mult}
        if filter:
            kwargs["filter"] = filter
        return self.store.max_marginal_relevance_search(query, **kwargs)
