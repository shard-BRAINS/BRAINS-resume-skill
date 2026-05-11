"""PDF resume parser.

Extracts text and detects section structure from a resume PDF using pdfplumber.
Returns a dict with raw text, detected sections, and page count.

No OCR support — scanned-image PDFs are out of scope for v1.
"""
from pathlib import Path
from typing import Union

import pdfplumber

# Section heading vocabulary the parser recognises.
SECTION_KEYWORDS = {
    "summary", "profile", "objective", "about",
    "experience", "employment", "work history", "professional experience",
    "education", "academic", "qualifications",
    "skills", "technical skills", "competencies",
    "projects", "publications", "certifications", "languages",
    "achievements", "awards", "interests", "volunteer",
}


def parse_pdf_resume(path: Union[str, Path]) -> dict:
    """Parse a resume PDF and return structured content.

    Parameters
    ----------
    path : str or Path
        Path to a PDF file.

    Returns
    -------
    dict
        Keys: ``raw_text`` (str), ``sections`` (dict[str, str]), ``page_count`` (int).

    Raises
    ------
    FileNotFoundError
        If the PDF file does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    with pdfplumber.open(path) as pdf:
        page_count = len(pdf.pages)
        raw_text_parts = []
        for page in pdf.pages:
            text = page.extract_text() or ""
            raw_text_parts.append(text)
    raw_text = "\n".join(raw_text_parts)

    sections = _split_sections(raw_text)
    return {
        "raw_text": raw_text,
        "sections": sections,
        "page_count": page_count,
    }


def _split_sections(raw_text: str) -> dict:
    """Heuristic section splitter — looks for short lines that match the
    section-keyword vocabulary and treats them as headings."""
    sections: dict = {}
    current_heading = "_preamble"
    current_lines: list = []

    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            current_lines.append(line)
            continue
        # Heading heuristic: short line (<=40 chars), matches a keyword.
        if len(stripped) <= 40:
            lower = stripped.lower().rstrip(":")
            if lower in SECTION_KEYWORDS:
                # Flush current section.
                if current_lines:
                    sections[current_heading] = "\n".join(current_lines).strip()
                current_heading = lower
                current_lines = []
                continue
        current_lines.append(line)

    if current_lines:
        sections[current_heading] = "\n".join(current_lines).strip()

    return sections
