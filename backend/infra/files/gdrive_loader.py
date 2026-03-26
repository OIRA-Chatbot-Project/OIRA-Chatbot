"""
Utilities for loading and processing Google Docs.

This module handles fetching Google Docs via their export URLs, converting
them to Markdown, and caching them locally.
"""
import csv
import os
import re
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import requests
from langchain_core.documents import Document
from markdownify import markdownify as to_markdown

from core.settings import settings


_GDOC_ID_RE = re.compile(r"/d/([a-zA-Z0-9_-]+)")


def _extract_gdoc_id(url: str) -> Optional[str]:
    """Extract the Google Doc ID from a URL.

    Args:
        url: The Google Doc URL.

    Returns:
        Optional[str]: The extracted document ID, or None if not found.
    """
    match = _GDOC_ID_RE.search(url or "")
    if match:
        return match.group(1)

    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if qs.get("id"):
        return qs["id"][0]

    return None


def _to_export_url(url: str) -> Optional[str]:
    """Convert a Google Doc URL to an export URL (HTML format).

    Args:
        url: The Google Doc URL.

    Returns:
        Optional[str]: The export URL, or None if the ID could not be extracted.
    """
    doc_id = _extract_gdoc_id(url)
    if not doc_id:
        return None
    return f"https://docs.google.com/document/d/{doc_id}/export?format=html"


def _read_google_docs_csv(path: str) -> List[Dict[str, str]]:
    """Read the Google Docs CSV file.

    Args:
        path: Path to the CSV file.

    Returns:
        List[Dict[str, str]]: A list of dictionaries representing the CSV rows.
    """
    if not os.path.exists(path):
        return []

    with open(path, "r", encoding="utf-8", newline="") as f:
        lines = [
            line
            for line in f
            if line.strip() and not line.lstrip().startswith("#")
        ]

    if not lines:
        return []

    reader = csv.DictReader(lines)
    entries: List[Dict[str, str]] = []
    for row in reader:
        url = (row.get("url") or row.get("link") or "").strip()
        if not url:
            continue

        filename = (row.get("filename") or row.get("name") or "").strip()
        doc_type = (row.get("doc_type") or "").strip()

        entries.append({"url": url, "filename": filename, "doc_type": doc_type})

    return entries


def _normalize_markdown(text: str) -> str:
    """Normalize the generated Markdown text.

    Args:
        text: The raw Markdown text.

    Returns:
        str: The normalized Markdown text.
    """
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def _fetch_google_doc_markdown(url: str, timeout: int = 30) -> str:
    """Fetch a Google Doc and convert it to Markdown.

    Args:
        url: The Google Doc URL.
        timeout: Request timeout in seconds.

    Returns:
        str: The converted Markdown content.

    Raises:
        ValueError: If the document ID cannot be extracted.
        requests.RequestException: If the network request fails.
    """
    export_url = _to_export_url(url)
    if not export_url:
        raise ValueError("Could not parse Google Docs document ID from URL")

    response = requests.get(export_url, timeout=timeout)
    response.raise_for_status()
    html = response.text

    markdown = to_markdown(html, heading_style="ATX", bullets="-")
    return _normalize_markdown(markdown)


def load_google_docs() -> List[Document]:
    """Load Google Docs defined in the configuration CSV.

    Reads the CSV file specified in settings.ingestion.GOOGLE_DOCS_CSV, fetches the
    documents (using cache if available), and returns them as LangChain Documents.

    Returns:
        List[Document]: A list of loaded documents.
    """
    entries = _read_google_docs_csv(settings.ingestion.GOOGLE_DOCS_CSV)
    if not entries:
        return []

    os.makedirs(settings.ingestion.GOOGLE_DOCS_CACHE_DIR, exist_ok=True)

    docs: List[Document] = []
    for entry in entries:
        url = entry.get("url", "")
        filename = entry.get("filename", "")
        doc_type = entry.get("doc_type", "")

        if not url:
            print(f"[WARNING] Skipping Google Doc entry with empty URL: '{filename or 'unknown'}'")
            continue

        doc_id = _extract_gdoc_id(url)
        base = filename or (f"gdoc-{doc_id}" if doc_id else "gdoc")
        safe_base = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("_")
        if not safe_base.endswith(".md"):
            safe_base += ".md"

        cache_path = os.path.join(settings.ingestion.GOOGLE_DOCS_CACHE_DIR, safe_base)

        try:
            if os.path.exists(cache_path) and not settings.ingestion.GOOGLE_DOCS_REFRESH:
                with open(cache_path, "r", encoding="utf-8") as f:
                    markdown = f.read()
            else:
                markdown = _fetch_google_doc_markdown(url)
                with open(cache_path, "w", encoding="utf-8") as f:
                    f.write(markdown + "\n")
        except Exception as e:
            print(f"[WARNING] Failed to load Google Doc '{filename or safe_base}': {e}")
            continue

        if not markdown.strip():
            continue

        docs.append(
            Document(
                page_content=markdown,
                metadata={
                    "source": filename or safe_base,
                    "source_url": url,
                    "doc_type": doc_type,
                    "page": 0,
                },
            )
        )

    return docs
