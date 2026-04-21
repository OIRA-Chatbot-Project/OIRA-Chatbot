from src.repository.orm import CatalogDocumentRecord, DocumentRecord


def test_document_record_supports_catalog_metadata() -> None:
    record = DocumentRecord(
        document_id="doc-2026-001",
        document_type="catalog",
        file_name="catalog-2026.pdf",
        content_type="application/pdf",
        storage_uri="s3://bucket/catalog-2026.pdf",
        uploaded_by="pipeline",
        catalog_year="2026-2027",
        catalog_version_id="2026-2027-v1",
        metadata={"ingestion_job_id": "job-123"},
    )

    assert record.document_type == "catalog"
    assert record.catalog_year == "2026-2027"
    assert record.catalog_version_id == "2026-2027-v1"
    assert record.metadata["ingestion_job_id"] == "job-123"


def test_catalog_document_record_alias_is_compatible() -> None:
    assert CatalogDocumentRecord is DocumentRecord
