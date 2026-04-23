from __future__ import annotations
from langchain_openai import OpenAIEmbeddings
from src.repository.abstract_repository import BaseRepository
from langchain_chroma import Chroma
from src.repository.orm import (
    CatalogChunkRecord, 
    DocumentRecord
)


class ChromaKnowledgeRepository(BaseRepository[CatalogChunkRecord, str]):
    def __init__(
        self,
        *,
        collection_name: str,
        embedding_model: str = "text-embedding-3-large",
        persist_directory: str | None = "./chroma_langchain_db"
    ) -> None:
        self._embeddings = OpenAIEmbeddings(model=embedding_model)
        self._vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=self._embeddings,
            persist_directory=persist_directory,
        )





# TO DO: merge belows into KnowledgeRepository 


#     """Vector-store repository for semantic retrieval over catalog chunks."""
#     def create(self, entity: CatalogChunkRecord) -> CatalogChunkRecord:
#         raise NotImplementedError("TODO: implement CatalogVectorRepository.create")

#     def get_by_id(self, entity_id: str) -> CatalogChunkRecord | None:
#         raise NotImplementedError("TODO: implement CatalogVectorRepository.get_by_id")

#     def update(self, entity: CatalogChunkRecord) -> CatalogChunkRecord:
#         raise NotImplementedError("TODO: implement CatalogVectorRepository.update")

#     def delete(self, entity_id: str) -> None:
#         raise NotImplementedError("TODO: implement CatalogVectorRepository.delete")

#     def list(self, limit: int = 100, offset: int = 0) -> list[CatalogChunkRecord]:
#         raise NotImplementedError("TODO: implement CatalogVectorRepository.list")

#     def has_catalog_index(self, catalog_version_id: str) -> bool:
#         """Check whether an index exists for a catalog snapshot."""
#         raise NotImplementedError(
#             "TODO: implement CatalogVectorRepository.has_catalog_index"
#         )

#     def get_or_create_catalog_index(self, catalog_version_id: str) -> str:
#         """Return index/collection identifier for a catalog snapshot."""
#         raise NotImplementedError(
#             "TODO: implement CatalogVectorRepository.get_or_create_catalog_index"
#         )

#     def upsert_course_chunks(
#         self, chunks: list[CatalogChunkRecord], catalog_version_id: str
#     ) -> list[CatalogChunkRecord]:
#         """Batch insert/update vector chunks for one catalog snapshot."""
#         raise NotImplementedError(
#             "TODO: implement CatalogVectorRepository.upsert_course_chunks"
#         )

#     def similarity_search(
#         self,
#         query: str,
#         catalog_version_id: str,
#         limit: int = 8,
#         filters: dict[str, str] | None = None,
#     ) -> list[CatalogChunkRecord]:
#         """Nearest-neighbor retrieval over embedded chunks."""
#         raise NotImplementedError(
#             "TODO: implement CatalogVectorRepository.similarity_search"
#         )

#     def mmr_search(
#         self,
#         query: str,
#         catalog_version_id: str,
#         limit: int = 8,
#         fetch_k: int = 24,
#     ) -> list[CatalogChunkRecord]:
#         """Maximal Marginal Relevance retrieval for diverse context windows."""
#         raise NotImplementedError("TODO: implement CatalogVectorRepository.mmr_search")

#     def delete_by_catalog_version(self, catalog_version_id: str) -> None:
#         """Delete all vectors associated with one catalog snapshot."""
#         raise NotImplementedError(
#             "TODO: implement CatalogVectorRepository.delete_by_catalog_version"
#         )




# class DocumentRepository(BaseRepository[DocumentRecord, str]):
#     """Repository for generic source document metadata and lifecycle."""

#     def create(self, entity: DocumentRecord) -> DocumentRecord:
#         raise NotImplementedError("TODO: implement DocumentRepository.create")

#     def get_by_id(self, entity_id: str) -> DocumentRecord | None:
#         raise NotImplementedError("TODO: implement DocumentRepository.get_by_id")

#     def update(self, entity: DocumentRecord) -> DocumentRecord:
#         raise NotImplementedError("TODO: implement DocumentRepository.update")

#     def delete(self, entity_id: str) -> None:
#         raise NotImplementedError("TODO: implement DocumentRepository.delete")

#     def list(self, limit: int = 100, offset: int = 0) -> list[DocumentRecord]:
#         raise NotImplementedError("TODO: implement DocumentRepository.list")

#     def list_by_user(self, user_id: str) -> list[DocumentRecord]:
#         """List documents uploaded by a specific user."""
#         raise NotImplementedError("TODO: implement DocumentRepository.list_by_user")

#     def list_by_document_type(self, document_type: str) -> list[DocumentRecord]:
#         """List documents scoped to one document type."""
#         raise NotImplementedError(
#             "TODO: implement DocumentRepository.list_by_document_type"
#         )

#     def delete_by_user(self, user_id: str) -> None:
#         """Delete all document records owned by a user."""
#         raise NotImplementedError("TODO: implement DocumentRepository.delete_by_user")
