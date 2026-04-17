from __future__ import annotations
from src.repository.course_repository import CatalogDocumentRepository, CourseRepository
from src.repository.knowledge_repository import CatalogVectorRepository
from src.repository.orm import CatalogDocumentRecord, CourseRecord
from src.repository.unit_of_work import UnitOfWork

class CatalogIngestionService:
    """Ingests catalog files and updates structured/vector stores."""
    def __init__(
        self,
        document_repository: CatalogDocumentRepository,
        course_repository: CourseRepository,
        vector_repository: CatalogVectorRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self.document_repository = document_repository
        self.course_repository = course_repository
        self.vector_repository = vector_repository
        self.unit_of_work = unit_of_work

    async def ingest_catalog_document(
        self,
        user_id: str,
        catalog_version_id: str,
        file_name: str,
        content_type: str,
        raw_text: str,
    ) -> CatalogDocumentRecord:
        with self.unit_of_work:
            return await self._ingest_catalog_document_in_transaction(
                user_id=user_id,
                catalog_version_id=catalog_version_id,
                file_name=file_name,
                content_type=content_type,
                raw_text=raw_text,
            )

    def normalize_courses(self, raw_text: str) -> list[CourseRecord]:
        raise NotImplementedError("TODO: implement CatalogIngestionService.normalize_courses")

    def index_course_embeddings(
        self, courses: list[CourseRecord], catalog_version_id: str
    ) -> None:
        raise NotImplementedError(
            "TODO: implement CatalogIngestionService.index_course_embeddings"
        )

    def get_document(self, document_id: str) -> CatalogDocumentRecord | None:
        raise NotImplementedError("TODO: implement CatalogIngestionService.get_document")

    def list_user_documents(self, user_id: str) -> list[CatalogDocumentRecord]:
        raise NotImplementedError(
            "TODO: implement CatalogIngestionService.list_user_documents"
        )

    def delete_document(self, document_id: str) -> None:
        with self.unit_of_work:
            self._delete_document_in_transaction(document_id=document_id)

    def delete_user_documents(self, user_id: str) -> None:
        with self.unit_of_work:
            self._delete_user_documents_in_transaction(user_id=user_id)

    async def _ingest_catalog_document_in_transaction(
        self,
        user_id: str,
        catalog_version_id: str,
        file_name: str,
        content_type: str,
        raw_text: str,
    ) -> CatalogDocumentRecord:
        raise NotImplementedError(
            "TODO: implement CatalogIngestionService._ingest_catalog_document_in_transaction"
        )

    def _delete_document_in_transaction(self, document_id: str) -> None:
        raise NotImplementedError(
            "TODO: implement CatalogIngestionService._delete_document_in_transaction"
        )

    def _delete_user_documents_in_transaction(self, user_id: str) -> None:
        raise NotImplementedError(
            "TODO: implement CatalogIngestionService._delete_user_documents_in_transaction"
        )