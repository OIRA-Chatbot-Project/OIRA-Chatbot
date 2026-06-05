"""Admin routes: database ingestion trigger."""
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_document_service
from app.core.auth import get_current_user
from app.services.document_service import DocumentService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/ingest")
async def trigger_ingestion(
    current_user: dict = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
):
    """Trigger the document ingestion pipeline (admin only)."""
    result = await document_service.run_ingestion()
    if not result.success:
        raise HTTPException(status_code=500, detail=result.message)
    return {"message": result.message}
