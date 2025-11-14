import io
import os
import re
from typing import List, Dict

from PIL import Image

try:
    import pytesseract
except Exception:  # pragma: no cover - fallback when pytesseract missing
    pytesseract = None


SUPPORTED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.gif'}
SUPPORTED_TEXT_EXTENSIONS = {'.txt', '.csv'}

COURSE_PATTERN = re.compile(r'(?P<code>[A-Z]{2,4}\s?\d{3})', re.IGNORECASE)
TERM_PATTERN = re.compile(r'(Fall|Spring|Summer|Winter)\s*(\d{2,4})?', re.IGNORECASE)


def extract_text_from_upload(content: bytes, filename: str) -> str:
    """
    Extract raw text from an uploaded file. Supports common image formats and plain text/csv files.
    """
    if not content:
        raise ValueError("Uploaded file is empty.")

    _, ext = os.path.splitext(filename.lower())

    if ext in SUPPORTED_TEXT_EXTENSIONS:
        return content.decode('utf-8', errors='ignore')

    if ext in SUPPORTED_IMAGE_EXTENSIONS:
        if pytesseract is None:
            raise ValueError(
                "Image OCR requires pytesseract. Please install it by adding 'pytesseract' "
                "and ensure the Tesseract OCR binary is available on your system PATH."
            )
        image = Image.open(io.BytesIO(content))
        text = pytesseract.image_to_string(image)
        return text

    raise ValueError(
        "Unsupported file type. Please upload an image (PNG/JPG) or a text/CSV export of your schedule."
    )


def parse_schedule_entries(raw_text: str) -> List[Dict[str, str]]:
    """
    Parse OCR'd schedule text into structured course entries.
    """
    entries: List[Dict[str, str]] = []
    if not raw_text:
        return entries

    for line in raw_text.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue

        course_match = COURSE_PATTERN.search(cleaned)
        if not course_match:
            continue

        course_code = course_match.group('code').upper().replace(' ', '')
        course_code = f"{course_code[:-3]} {course_code[-3:]}"

        term_match = TERM_PATTERN.search(cleaned)
        term = None
        if term_match:
            term = term_match.group(0).title()

        entries.append({
            "course_code": course_code,
            "term": term,
            "notes": cleaned
        })

    return entries


def summarize_schedule(entries: List[Dict[str, str]]) -> str:
    """
    Build a human-readable summary of parsed courses.
    """
    if not entries:
        return "No readable courses were detected in the uploaded schedule."

    lines = []
    for entry in entries:
        parts = [entry["course_code"]]
        if entry.get("term"):
            parts.append(f"({entry['term']})")
        detail = " ".join(parts)
        if entry.get("notes"):
            detail = f"{detail} — {entry['notes']}"
        lines.append(f"- {detail}")
    return "\n".join(lines)
