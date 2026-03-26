"""RAG constants: document type mappings, regex patterns, section patterns."""
import re

DOCUMENT_TYPE_MAPPINGS = {
    "catalog": [
        "2025-2026 course catalog.pdf",
        "datalab-output-2025-2026 course catalog.pdf.md",
    ],
    "policy": [
        "ACADEMIC RESPONSIBILITY POLICY.pdf",
        "ACADEMIC STANDING.pdf",
        "ADVANCED PLACEMENT & CREDIT POLICY.pdf",
        "CLASS ATTENDANCE POLICY.pdf",
        "COLLEGE LEVEL EXAMINATION PROGRAM (CLEP) POLICY.pdf",
        "COURSE REGISTRATION & WITHDRAWAL POLICY.pdf",
        "CREDIT BY EXAMINATION POLICY.pdf",
        "DECLARATION OF A MINOR POLICY.pdf",
        "DEGREE & GRADUATION REQUIREMENTS POLICY.pdf",
        "DOUBLE COUNTING COURSES POLICY.pdf",
        "GRADE APPEALS POLICY.pdf",
        "GRADE REPLACEMENT POLICY.pdf",
        "INCOMPLETE GRADES POLICY.pdf",
        "INTERNATIONAL BACCALAUREATE (IB) & CAMBRIDGE INTERNATIONAL A LEVEL CREDIT POLICY.pdf",
        "SUPERIOR ACADEMIC ACHIEVEMENT (Honors Designations) POLICY.pdf",
        "TRANSFER OF ACADEMIC CREDIT.pdf",
        "WITHDRAWAL, LEAVE OF ABSENCE & SUSPENSION POLICY.pdf",
    ],
}

COURSE_START_RE = re.compile(r'(?m)^(?:#{1,6}\s+\*{0,2})?(?P<code>[A-Z]{2,4}\s?\d{3}[A-Z]?)\s*[:\.\-]\s+')
PAGE_MARKER_MD_RE = re.compile(r'^\{(\d+)\}-+', re.MULTILINE)
PAGE_MARKER_RE = re.compile(r'\[\[PAGE:(\d+)\]\]')

SECTION_PATTERNS = {
    "freeman_core": [
        "freeman college core curriculum",
        "freeman college of management core curriculum",
        "freeman college core requirements",
    ],
    "sequence": [
        "recommended sequence",
        "four-year plan",
        "four year plan",
        "first year",
        "sophomore year",
        "junior year",
        "senior year",
    ],
    "major_requirements": [
        "major requirements",
        "business analytics major requirements",
    ],
}
