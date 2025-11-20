from fastapi import APIRouter, HTTPException
import subprocess

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/ingest")
async def trigger_ingestion():
    """
    Trigger re-ingestion of PDFs from data/ folder
    
    Note: This is a placeholder. In production, you might want to:
    - Add authentication/authorization
    - Run ingestion in background task
    - Return job status
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
