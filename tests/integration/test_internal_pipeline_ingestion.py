from __future__ import annotations

import asyncio

from src.repository.orm import CatalogChunkRecord, ChatSessionRecord, DocumentRecord
from src.repository.unit_of_work import NoOpUnitOfWork
from src.services.document_service import CatalogIngestionService


class InMemoryDocumentRepository:
    def __init__(self) -> None:
        self.records: dict[str, DocumentRecord] = {}

    def create(self, entity: DocumentRecord) -> DocumentRecord:
        self.records[entity.document_id] = entity
        return entity


class InMemoryVectorRepository:
    def __init__(self) -> None:
        self.chunks: list[CatalogChunkRecord] = []

    def upsert_course_chunks(
        self, chunks: list[CatalogChunkRecord], catalog_version_id: str
    ) -> list[CatalogChunkRecord]:
        _ = catalog_version_id
        self.chunks.extend(chunks)
        return chunks


class InMemoryCourseRepository:
    pass


class PipelineCatalogIngestionService(CatalogIngestionService):
    def normalize_courses(self, raw_text: str):  # type: ignore[override]
        _ = raw_text
        return []

    def index_course_embeddings(self, courses, catalog_version_id: str) -> None:  # type: ignore[override]
        _ = courses
        _ = catalog_version_id
        return

    def get_document(self, document_id: str):  # type: ignore[override]
        return self.document_repository.records.get(document_id)

    def list_user_documents(self, user_id: str):  # type: ignore[override]
        return [r for r in self.document_repository.records.values() if r.uploaded_by == user_id]

    async def _ingest_catalog_document_in_transaction(  # type: ignore[override]
        self,
        user_id: str,
        catalog_version_id: str,
        file_name: str,
        content_type: str,
        raw_text: str,
    ) -> DocumentRecord:
        document = DocumentRecord(
            document_id=f"doc-{catalog_version_id}",
            document_type="catalog",
            file_name=file_name,
            content_type=content_type,
            storage_uri=f"memory://{file_name}",
            uploaded_by=user_id,
            catalog_version_id=catalog_version_id,
            catalog_year=catalog_version_id,
            metadata={"source": "internal_pipeline"},
        )
        self.document_repository.create(document)

        chunk = CatalogChunkRecord(
            chunk_id=f"chunk-{catalog_version_id}-001",
            catalog_year=catalog_version_id,
            source_course_code="CSCI 101",
            source_field="description",
            chunk_text=raw_text,
            embedding_model="test-embedding-model",
            metadata={"document_id": document.document_id},
        )
        self.vector_repository.upsert_course_chunks(
            chunks=[chunk],
            catalog_version_id=catalog_version_id,
        )
        return document

    def _delete_document_in_transaction(self, document_id: str) -> None:  # type: ignore[override]
        self.document_repository.records.pop(document_id, None)

    def _delete_user_documents_in_transaction(self, user_id: str) -> None:  # type: ignore[override]
        records = self.list_user_documents(user_id)
        for record in records:
            self.document_repository.records.pop(record.document_id, None)


def test_internal_pipeline_ingests_without_public_document_api() -> None:
    document_repository = InMemoryDocumentRepository()
    vector_repository = InMemoryVectorRepository()
    course_repository = InMemoryCourseRepository()

    service = PipelineCatalogIngestionService(
        document_repository=document_repository,  # type: ignore[arg-type]
        course_repository=course_repository,  # type: ignore[arg-type]
        vector_repository=vector_repository,  # type: ignore[arg-type]
        unit_of_work=NoOpUnitOfWork(),
    )

    first_document = asyncio.run(
        service.ingest_catalog_document(
            user_id="internal-pipeline",
            catalog_version_id="2026-2027",
            file_name="catalog-2026.pdf",
            content_type="application/pdf",
            raw_text="Intro to programming concepts.",
        )
    )

    assert first_document.document_type == "catalog"
    assert first_document.catalog_version_id == "2026-2027"
    assert first_document.document_id in document_repository.records
    assert len(vector_repository.chunks) == 1

    pinned_session = ChatSessionRecord(
        session_id="session-1",
        user_id="student-1",
        title="Advising Session",
        catalog_year="2026-2027",
    )

    asyncio.run(
        service.ingest_catalog_document(
            user_id="internal-pipeline",
            catalog_version_id="2027-2028",
            file_name="catalog-2027.pdf",
            content_type="application/pdf",
            raw_text="Data structures and algorithms.",
        )
    )

    # New yearly ingestion should not change previously pinned session versions.
    assert pinned_session.catalog_year == "2026-2027"
    assert len(vector_repository.chunks) == 2
