"""
Administrative routes.
"""
from fastapi import APIRouter, HTTPException
import subprocess
import os

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/ingest")
async def trigger_ingestion():
    """Trigger re-ingestion of documents into the vector database."""
    try:
        # Try new pipeline script first, fall back to legacy ingest_database.py
        scripts_ingest = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "ingest.py")
        legacy_ingest = "ingest_database.py"

        if os.path.exists(scripts_ingest):
            script = scripts_ingest
        else:
            script = legacy_ingest

        result = subprocess.run(
            ["python", script],
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error triggering ingestion: {str(e)}")
