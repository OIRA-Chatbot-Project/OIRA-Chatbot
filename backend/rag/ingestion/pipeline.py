"""RAG ingestion pipeline orchestrator."""
import os
from core.settings import settings
from rag.ingestion.classifiers import classify_document_type
from rag.ingestion.loaders import load_pdf_documents, load_markdown_catalog_documents, load_google_docs
from rag.ingestion.enrichers import assign_section_metadata, extract_course_documents
from rag.ingestion.chunkers import Chunker
from rag.ingestion.vector_sink import VectorSink


class Pipeline:
    """Orchestrates the full ingestion pipeline."""

    def __init__(self, data_path: str = None, chroma_path: str = None, collection_name: str = None):
        self.data_path = data_path or settings.ingestion.DATA_PATH
        self.chroma_path = chroma_path or settings.vector.CHROMA_PATH
        self.collection_name = collection_name or settings.vector.CHROMA_COLLECTION_NAME

    def run(self) -> None:
        """Run the full ingestion pipeline."""
        from infra.vectorstores.chroma import get_chroma_store
        vector_store = get_chroma_store(self.chroma_path, self.collection_name)

        pdf_documents = []
        markdown_documents = []
        if not settings.ingestion.GOOGLE_DOCS_ONLY:
            markdown_documents, superseded_pdfs = load_markdown_catalog_documents(self.data_path)
            pdf_documents = load_pdf_documents(self.data_path)
            filtered_pdfs = []
            for doc in pdf_documents:
                source_path = doc.metadata.get("source", "")
                filename = os.path.basename(source_path)
                if classify_document_type(filename) == "catalog" and filename not in superseded_pdfs:
                    filtered_pdfs.append(doc)
            pdf_documents = filtered_pdfs
            print(f"Loaded {len(pdf_documents)} catalog pages from PDFs in {self.data_path}")
            print(f"Loaded {len(markdown_documents)} document(s) from markdown in {self.data_path}")

        google_docs = load_google_docs()
        if google_docs:
            print(f"Loaded {len(google_docs)} Google Docs")

        raw_documents = pdf_documents + markdown_documents + google_docs
        print(f"Total raw documents: {len(raw_documents)}")

        doc_type_counts = {"catalog": 0, "policy": 0}
        for doc in raw_documents:
            source_path = doc.metadata.get("source", "")
            filename = os.path.basename(source_path)
            existing_type = doc.metadata.get("doc_type")
            doc_type = existing_type or classify_document_type(filename)
            doc.metadata["doc_type"] = doc_type
            doc_type_counts[doc_type] = doc_type_counts.get(doc_type, 0) + 1
        print(f"Document classification: {doc_type_counts}")

        catalog_docs = [d for d in raw_documents if d.metadata.get("doc_type") == "catalog"]
        course_docs = extract_course_documents(catalog_docs)

        chunker = Chunker()
        chunks = chunker.split(raw_documents)
        print(f"Created {len(chunks)} chunks")

        for c in chunks:
            if c.metadata.get("doc_type") == "catalog":
                section = assign_section_metadata(c.page_content)
                if section:
                    c.metadata["section"] = section

        if course_docs:
            for c in course_docs:
                section = assign_section_metadata(c.page_content)
                if section:
                    c.metadata["section"] = section
            chunks.extend(course_docs)
            print(f"Total chunks after adding course entries: {len(chunks)}")

        sink = VectorSink(vector_store)
        sink.upsert(chunks)
        print(f"Ingestion complete. {len(chunks)} chunks added to '{self.collection_name}'.")
