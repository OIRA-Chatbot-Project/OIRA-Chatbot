"""CLI wrapper for the ingestion pipeline."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.ingestion.pipeline import Pipeline

if __name__ == "__main__":
    pipeline = Pipeline()
    pipeline.run()
