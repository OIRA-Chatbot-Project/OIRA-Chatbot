from __future__ import annotations
from fastapi import APIRouter, Depends
from src.api_endpoints.dependencies import get_catalog_ingestion_service
from src.api_endpoints.schemas import (
    CatalogDocumentResponse,
    CatalogUploadRequest,
    CatalogUploadResponse,
)
from src.services.document_service import CatalogIngestionService

router = APIRouter(prefix="/api/document", tags=["catalog"])

@router.post("/upload", response_model=CatalogUploadResponse)
async def upload_catalog(
    request: CatalogUploadRequest,
    ingestion_service: CatalogIngestionService = Depends(get_catalog_ingestion_service),
) -> CatalogUploadResponse:
    """Upload and ingest a course catalog source document."""
    _ = request
    _ = ingestion_service
    raise NotImplementedError("TODO: implement upload_catalog")

@router.get("/download/{document_id}", response_model=CatalogDocumentResponse)
async def download_document(
    document_id: str,
    ingestion_service: CatalogIngestionService = Depends(get_catalog_ingestion_service),
) -> CatalogDocumentResponse:
    """Retrieve metadata for one uploaded catalog document."""
    _ = document_id
    _ = ingestion_service
    raise NotImplementedError("TODO: implement download_document")

@router.get("/list/{user_id}", response_model=list[CatalogDocumentResponse])
async def list_documents(
    user_id: str,
    ingestion_service: CatalogIngestionService = Depends(get_catalog_ingestion_service),
) -> list[CatalogDocumentResponse]:
    """List catalog documents uploaded by a specific user."""
    _ = user_id
    _ = ingestion_service
    raise NotImplementedError("TODO: implement list_documents")

@router.delete("/delete/{document_id}")
async def delete_document(
    document_id: str,
    ingestion_service: CatalogIngestionService = Depends(get_catalog_ingestion_service),
) -> dict[str, str]:
    """Delete one catalog document and associated knowledge entries."""
    _ = document_id
    _ = ingestion_service
    raise NotImplementedError("TODO: implement delete_document")

@router.delete("/delete_all/{user_id}")
async def delete_all_documents(
    user_id: str,
    ingestion_service: CatalogIngestionService = Depends(get_catalog_ingestion_service),
) -> dict[str, str]:
    """Delete all catalog documents and associated knowledge for one user."""
    _ = user_id
    _ = ingestion_service
    raise NotImplementedError("TODO: implement delete_all_documents")