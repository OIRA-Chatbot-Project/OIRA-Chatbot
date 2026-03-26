"""Vector store sink for batch upsert."""
from uuid import uuid4
from typing import List
from langchain_core.documents import Document

BATCH_SIZE = 100


class VectorSink:
    """Handles batch upsert of documents to a vector store."""
    def __init__(self, vector_store):
        self.vector_store = vector_store

    def upsert(self, documents: List[Document]) -> None:
        total = len(documents)
        uuids = [str(uuid4()) for _ in range(total)]
        print(f"Total chunks to upsert: {total}")
        for i in range(0, total, BATCH_SIZE):
            j = min(i + BATCH_SIZE, total)
            batch_chunks = documents[i:j]
            batch_ids = uuids[i:j]
            print(f"Adding batch {i//BATCH_SIZE + 1}: chunks {i+1}-{j}")
            self.vector_store.add_documents(documents=batch_chunks, ids=batch_ids)
        print(f"Added {total} chunks.")
