"""Cover-letter DOCX generator.

Fills the cover-letter template with structured letter data. UNBRANDED —
this is the user's professional document submitted to employers.
"""
from pathlib import Path
from typing import Union

from docx import Document


DEFAULT_TEMPLATE = "formal-business"
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates" / "cover-letter"


PLACEHOLDER_MAP = {
    "candidate_name": "{{CANDIDATE_NAME}}",
    "candidate_contact_line": "{{CANDIDATE_CONTACT_LINE}}",
    "letter_date": "{{LETTER_DATE}}",
    "recipient_name": "{{RECIPIENT_NAME}}",
    "recipient_title": "{{RECIPIENT_TITLE}}",
    "recipient_company": "{{RECIPIENT_COMPANY}}",
    "salutation": "{{SALUTATION}}",
    "hook_paragraph": "{{HOOK_PARAGRAPH}}",
    "fit_paragraph": "{{FIT_PARAGRAPH}}",
    "close_paragraph": "{{CLOSE_PARAGRAPH}}",
}


def render_cover_letter_docx(data: dict, out_path: Union[str, Path]) -> Path:
    """Fill the cover-letter template with letter data and save."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    template_path = TEMPLATES_DIR / f"{DEFAULT_TEMPLATE}.docx"
    if not template_path.exists():
        raise FileNotFoundError(f"Cover-letter template not found: {template_path}")

    doc = Document(str(template_path))

    for paragraph in doc.paragraphs:
        for key, placeholder in PLACEHOLDER_MAP.items():
            if placeholder in paragraph.text:
                value = data.get(key, "") or ""
                if paragraph.runs:
                    full = paragraph.text.replace(placeholder, value)
                    for run in paragraph.runs[1:]:
                        run.text = ""
                    paragraph.runs[0].text = full

    doc.save(str(out_path))
    return out_path
