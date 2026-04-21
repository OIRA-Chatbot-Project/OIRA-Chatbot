from __future__ import annotations
from fastapi import APIRouter, HTTPException, status
from src.api_endpoints.schemas import (
    CatalogDocumentResponse,
    CatalogUploadRequest,
    CatalogUploadResponse,
)

router = APIRouter(prefix="/api/document", tags=["catalog"])
DOCUMENT_API_DISABLED_MESSAGE = (
    "Document ingestion API is disabled. Catalog ingestion is managed by the internal yearly pipeline."
)


def _raise_document_api_disabled() -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=DOCUMENT_API_DISABLED_MESSAGE,
    )


@router.post("/upload", response_model=CatalogUploadResponse)
async def upload_catalog(
    request: CatalogUploadRequest,
) -> CatalogUploadResponse:
    """Reserved for future RAG uploads; disabled in current release."""
    _ = request
    _raise_document_api_disabled()

@router.get("/download/{document_id}", response_model=CatalogDocumentResponse)
async def download_document(
    document_id: str,
) -> CatalogDocumentResponse:
    """Reserved for future RAG document download; disabled in current release."""
    _ = document_id
    _raise_document_api_disabled()

@router.get("/list/{user_id}", response_model=list[CatalogDocumentResponse])
async def list_documents(
    user_id: str,
) -> list[CatalogDocumentResponse]:
    """Reserved for future RAG document listing; disabled in current release."""
    _ = user_id
    _raise_document_api_disabled()

@router.delete("/delete/{document_id}")
async def delete_document(
    document_id: str,
) -> dict[str, str]:
    """Reserved for future RAG document deletion; disabled in current release."""
    _ = document_id
    _raise_document_api_disabled()

@router.delete("/delete_all/{user_id}")
async def delete_all_documents(
    user_id: str,
) -> dict[str, str]:
    """Reserved for future RAG bulk document deletion; disabled in current release."""
    _ = user_id
    _raise_document_api_disabled()
