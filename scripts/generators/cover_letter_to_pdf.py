"""Cover-letter PDF generator.

Renders a clean business-letter PDF directly via reportlab. UNBRANDED.
"""
from pathlib import Path
from typing import Union

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer


BODY_COLOUR = HexColor("#1A1A1A")


def _make_styles():
    name_style = ParagraphStyle(
        name="LetterName", fontName="Helvetica", fontSize=14,
        textColor=BODY_COLOUR, spaceAfter=2,
    )
    contact_style = ParagraphStyle(
        name="LetterContact", fontName="Helvetica", fontSize=10,
        textColor=BODY_COLOUR, spaceAfter=14,
    )
    body_style = ParagraphStyle(
        name="LetterBody", fontName="Helvetica", fontSize=11,
        textColor=BODY_COLOUR, leading=15, spaceAfter=10,
    )
    return name_style, contact_style, body_style


def render_cover_letter_pdf(data: dict, out_path: Union[str, Path]) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    name_s, contact_s, body_s = _make_styles()
    doc = SimpleDocTemplate(
        str(out_path), pagesize=letter,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        title=f"{data.get('candidate_name', 'Cover Letter')} - Cover Letter",
        author=data.get("candidate_name", ""),
    )
    story = []
    story.append(Paragraph(data.get("candidate_name", ""), name_s))
    story.append(Paragraph(data.get("candidate_contact_line", ""), contact_s))
    story.append(Paragraph(data.get("letter_date", ""), body_s))

    recipient_lines = [
        data.get("recipient_name", ""),
        data.get("recipient_title", ""),
        data.get("recipient_company", ""),
    ]
    for line in recipient_lines:
        if line:
            story.append(Paragraph(line, body_s))
    story.append(Spacer(1, 6))

    salutation = data.get("salutation", "Hiring Team")
    story.append(Paragraph(f"Dear {salutation},", body_s))

    for key in ("hook_paragraph", "fit_paragraph", "close_paragraph"):
        if data.get(key):
            story.append(Paragraph(data[key], body_s))

    story.append(Spacer(1, 8))
    story.append(Paragraph("Sincerely,", body_s))
    story.append(Spacer(1, 16))
    story.append(Paragraph(data.get("candidate_name", ""), body_s))

    doc.build(story)
    return out_path
