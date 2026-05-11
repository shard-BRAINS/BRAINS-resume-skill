"""DOCX resume parser.

Extracts text and detects section structure from a resume DOCX using python-docx.
Returns a dict with raw text, detected sections, and paragraph count.
"""
from pathlib import Path
from typing import Union

from docx import Document

SECTION_KEYWORDS = {
    "summary", "profile", "objective", "about",
    "experience", "employment", "work history", "professional experience",
    "education", "academic", "qualifications",
    "skills", "technical skills", "competencies",
    "projects", "publications", "certifications", "languages",
    "achievements", "awards", "interests", "volunteer",
}


def parse_docx_resume(path: Union[str, Path]) -> dict:
    """Parse a resume DOCX and return structured content.

    Parameters
    ----------
    path : str or Path
        Path to a DOCX file.

    Returns
    -------
    dict
        Keys: ``raw_text`` (str), ``sections`` (dict[str, str]), ``paragraph_count`` (int).

    Raises
    ------
    FileNotFoundError
        If the DOCX file does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"DOCX not found: {path}")

    doc = Document(str(path))
    raw_text_parts: list = []
    sections: dict = {}
    current_heading = "_preamble"
    current_lines: list = []

    for paragraph in doc.paragraphs:
        text = paragraph.text
        raw_text_parts.append(text)
        # Detect heading: either a real heading style, OR short line matching keyword.
        style_name = (paragraph.style.name or "").lower()
        is_heading = style_name.startswith("heading") or style_name == "title"
        looks_like_heading = (
            len(text.strip()) <= 40
            and text.strip().lower().rstrip(":") in SECTION_KEYWORDS
        )
        if (is_heading and text.strip().lower().rstrip(":") in SECTION_KEYWORDS) or looks_like_heading:
            if current_lines:
                sections[current_heading] = "\n".join(current_lines).strip()
            current_heading = text.strip().lower().rstrip(":")
            current_lines = []
        else:
            current_lines.append(text)

    if current_lines:
        sections[current_heading] = "\n".join(current_lines).strip()

    return {
        "raw_text": "\n".join(raw_text_parts),
        "sections": sections,
        "paragraph_count": len(doc.paragraphs),
    }
