"""Text chunking for RAG ingestion."""
from langchain_text_splitters import RecursiveCharacterTextSplitter
from core.settings import settings


class Chunker:
    """Splits documents into chunks."""
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or 1200
        self.chunk_overlap = chunk_overlap or 200
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )

    def split(self, documents: list) -> list:
        return self._splitter.split_documents(documents)
