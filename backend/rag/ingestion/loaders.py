"""Document loaders for PDF, Markdown, and Google Docs."""
import os
import re
from typing import List, Tuple
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_core.documents import Document
from rag.constants import PAGE_MARKER_MD_RE
from core.settings import settings


def load_pdf_documents(data_path: str) -> List[Document]:
    """Load PDF documents from a directory."""
    loader = PyPDFDirectoryLoader(data_path)
    return loader.load()


def load_markdown_catalog_documents(data_path: str) -> Tuple[List[Document], set]:
    """Load markdown catalog files (datalab-output-*.md) from data directory.
    Returns (docs, superseded_pdf_basenames).
    """
    candidates: dict = {}
    for filename in os.listdir(data_path):
        if not (filename.startswith("datalab-output-") and filename.endswith(".md")):
            continue
        raw = filename[len("datalab-output-"):-len(".md")]
        pdf_name = re.sub(r'\s+\(\d+\)$', '', raw)
        filepath = os.path.join(data_path, filename)
        with open(filepath, encoding="utf-8") as f:
            text = f.read()
        page_markers = list(PAGE_MARKER_MD_RE.finditer(text))
        docs = []
        if page_markers:
            for i, m in enumerate(page_markers):
                page_num = int(m.group(1))
                start = m.end()
                end = page_markers[i + 1].start() if i + 1 < len(page_markers) else len(text)
                page_text = text[start:end].strip()
                if page_text:
                    docs.append(Document(
                        page_content=page_text,
                        metadata={"source": filepath, "doc_type": "catalog", "page": page_num},
                    ))
            print(f"Found markdown catalog: {filename} ({len(docs)} pages, supersedes '{pdf_name}')")
        else:
            docs.append(Document(
                page_content=text,
                metadata={"source": filepath, "doc_type": "catalog", "page": 0},
            ))
            print(f"Found markdown catalog: {filename} (no page markers, supersedes '{pdf_name}')")
        existing_count = candidates.get(pdf_name, ([], -1))[1]
        if len(docs) > existing_count:
            candidates[pdf_name] = (docs, len(docs))
    md_docs = []
    superseded_pdfs: set = set()
    for pdf_name, (docs, page_count) in candidates.items():
        superseded_pdfs.add(pdf_name)
        md_docs.extend(docs)
        print(f"Using markdown for '{pdf_name}': {page_count} page(s) loaded")
    return md_docs, superseded_pdfs


def load_google_docs() -> List[Document]:
    """Load Google Docs - delegates to infra/files/gdrive_loader.py."""
    from infra.files.gdrive_loader import load_google_docs as _load
    return _load()
