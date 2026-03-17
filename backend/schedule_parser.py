"""
Utilities for parsing student schedules from images or text.

This module provides functions to extract text from uploaded schedule images
(using OCR) or text files, and parse the extracted text into structured
course entries.
"""
import io
import os
import re
from typing import List, Dict

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

try:
    import pytesseract
except Exception:  # pragma: no cover - fallback when pytesseract missing
    pytesseract = None


SUPPORTED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.gif'}
SUPPORTED_TEXT_EXTENSIONS = {'.txt', '.csv'}

COURSE_PATTERN = re.compile(
    r'(?P<prefix>[A-Z]{2,4})[\s\-]*?(?P<number>\d{3}[A-Z]?)',
    re.IGNORECASE
)
TERM_PATTERN = re.compile(r'(Fall|Spring|Summer|Winter)\s*(\d{2,4})?', re.IGNORECASE)


def extract_text_from_upload(content: bytes, filename: str) -> str:
    """Extract raw text from an uploaded file.

    Supports common image formats and plain text/csv files.

    Args:
        content: The raw file content in bytes.
        filename: The original filename.

    Returns:
        str: The extracted text.

    Raises:
        ValueError: If the file is empty, unsupported, or if OCR fails.
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
        processed = _prepare_image_for_ocr(image)
        text = pytesseract.image_to_string(processed, lang='eng', config='--psm 6')
        text = text.strip()
        if not text:
            raise ValueError(
                "Could not read any text from the uploaded image. "
                "Try a clearer screenshot or export your schedule as text/CSV."
            )
        return text

    raise ValueError(
        "Unsupported file type. Please upload an image (PNG/JPG) or a text/CSV export of your schedule."
    )


def parse_schedule_entries(raw_text: str) -> List[Dict[str, str]]:
    """Parse OCR'd schedule text into structured course entries.

    Args:
        raw_text: The raw text extracted from the schedule.

    Returns:
        List[Dict[str, str]]: A list of dictionaries containing course details
        (course_code, term, notes).
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

        prefix = course_match.group('prefix').upper()
        number = course_match.group('number').upper().replace('-', '')
        course_code = f"{prefix} {number}"

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
    """Build a human-readable summary of parsed courses.

    Args:
        entries: A list of parsed course dictionaries.

    Returns:
        str: A formatted summary string suitable for the LLM.
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


def _prepare_image_for_ocr(image: Image.Image) -> Image.Image:
    """Enhance uploaded images to improve OCR accuracy.

    Args:
        image: The original PIL Image.

    Returns:
        Image.Image: The processed PIL Image.
    """
    image = ImageOps.exif_transpose(image)
    if image.mode not in ("L", "RGB"):
        image = image.convert("RGB")
    grayscale = ImageOps.grayscale(image)
    contrasted = ImageOps.autocontrast(grayscale)
    enhancer = ImageEnhance.Contrast(contrasted)
    contrasted = enhancer.enhance(1.8)

    width, height = contrasted.size
    max_dim = max(width, height)
    scale = 1
    if max_dim < 1200:
        scale = 2
    elif max_dim < 2000:
        scale = 1.5
    if scale != 1:
        contrasted = contrasted.resize(
            (int(width * scale), int(height * scale)),
            Image.Resampling.LANCZOS
        )

    sharpened = contrasted.filter(ImageFilter.SHARPEN)
    return sharpened
