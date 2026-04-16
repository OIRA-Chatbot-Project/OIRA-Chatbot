from fastapi import APIRouter, Request, HTTPException

router = APIRouter(prefix="/api/document")

@router.post("/upload")
async def upload_document():
    """Endpoint for uploading documents."""
    pass

@router.get("/download/{document_id}")
async def download_document(document_id: str):
    """Endpoint for downloading a specific document."""
    pass    

@router.get("/list/{user_id}")
async def list_documents(user_id: str):
    """Endpoint for listing documents for a specific user."""
    pass

@router.delete("/delete/{document_id}")
async def delete_document(document_id: str):
    """Endpoint for deleting a specific document."""
    pass

@router.delete("/delete_all/{user_id}")
async def delete_all_documents(user_id: str):    
    """Endpoint for deleting all documents for a specific user."""
    pass
