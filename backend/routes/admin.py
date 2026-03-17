"""
Administrative routes.

This module provides API endpoints for administrative tasks, such as triggering
database ingestion.
"""
from fastapi import APIRouter, HTTPException
import subprocess

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/ingest")
async def trigger_ingestion():
    """Trigger re-ingestion of documents into the vector database.
    
    This endpoint runs the ingestion script to process PDF documents and Google Docs,
    updating the Chroma vector database.

    Returns:
        dict: A success message if ingestion completes.

    Raises:
        HTTPException: If the ingestion process fails.
    """
    try:
        # Import and run ingestion script
        result = subprocess.run(
            ["python", "ingest_database.py"],
            capture_output=True,
            text=True,
            cwd="."
        )
        
        if result.returncode == 0:
            return {"success": True, "message": "Ingestion completed successfully"}
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Ingestion failed: {result.stderr}"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error triggering ingestion: {str(e)}")
