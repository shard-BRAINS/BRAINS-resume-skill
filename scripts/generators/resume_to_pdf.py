"""Resume PDF generator.

Renders an ATS-safe PDF directly from structured resume data using reportlab.
UNBRANDED — no BRAINS marks, no protected phrases, no Gold Deep accents.
"""
from pathlib import Path
from typing import Union

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer


BODY_COLOUR = HexColor("#1A1A1A")
MUTED = HexColor("#404040")


def _make_styles():
    name_style = ParagraphStyle(
        name="ResumeName", fontName="Helvetica", fontSize=22,
        textColor=BODY_COLOUR, spaceAfter=4,
    )
    contact_style = ParagraphStyle(
        name="ResumeContact", fontName="Helvetica", fontSize=10,
        textColor=MUTED, spaceAfter=14,
    )
    section_style = ParagraphStyle(
        name="ResumeSection", fontName="Helvetica-Bold", fontSize=12,
        textColor=BODY_COLOUR, spaceBefore=10, spaceAfter=6,
    )
    body_style = ParagraphStyle(
        name="ResumeBody", fontName="Helvetica", fontSize=11,
        textColor=BODY_COLOUR, leading=15,
    )
    return name_style, contact_style, section_style, body_style


def render_resume_pdf(data: dict, out_path: Union[str, Path]) -> Path:
    """Render a structured resume dict to an ATS-safe PDF."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    name_s, contact_s, section_s, body_s = _make_styles()

    doc = SimpleDocTemplate(
        str(out_path), pagesize=letter,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        title=f"{data.get('candidate_name', 'Resume')} - Resume",
        author=data.get("candidate_name", ""),
    )
    story = []

    story.append(Paragraph(data.get("candidate_name", ""), name_s))
    story.append(Paragraph(data.get("candidate_contact_line", ""), contact_s))

    story.append(Paragraph("Summary", section_s))
    story.append(Paragraph(data.get("summary", ""), body_s))

    story.append(Paragraph("Skills", section_s))
    story.append(Paragraph(data.get("skills", ""), body_s))

    story.append(Paragraph("Experience", section_s))
    for line in (data.get("experience") or "").splitlines():
        if line.strip():
            story.append(Paragraph(line, body_s))
        else:
            story.append(Spacer(1, 6))

    story.append(Paragraph("Education", section_s))
    for line in (data.get("education") or "").splitlines():
        if line.strip():
            story.append(Paragraph(line, body_s))

    doc.build(story)
    return out_path
