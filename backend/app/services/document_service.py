"""
DocumentService: triggers the ingestion pipeline asynchronously.
Replaces the blocking subprocess.run() in routes/admin.py.
"""
import asyncio
from dataclasses import dataclass


@dataclass
class IngestionResult:
    success: bool
    message: str


class DocumentService:
    async def run_ingestion(self) -> IngestionResult:
        """Run the ingestion pipeline in a thread pool to avoid blocking the event loop."""
        try:
            await asyncio.to_thread(self._run_sync)
            return IngestionResult(success=True, message="Ingestion completed successfully")
        except Exception as e:
            return IngestionResult(success=False, message=str(e))

    @staticmethod
    def _run_sync() -> None:
        from scripts.ingest_database import main as ingest_main
        ingest_main()
