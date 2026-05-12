"""Render a branded BRAINS coaching report PDF.

Reads styling parameters from references/brand-application.md:
- Body: Atkinson Hyperlegible (falls back to Helvetica if font not installed)
- Headings: Inter Bold (falls back to Helvetica-Bold)
- Heading colour: Gold Deep #D99518 on white
- BRAINS mark top-left header
- Footer with the protected origin phrase, verbatim
- Optional BRAINS Trust safeguarding-credit line above the footer
"""
from pathlib import Path
from typing import Union

from reportlab.lib.colors import HexColor, black, grey
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image,
)


GOLD_DEEP = HexColor("#D99518")
BODY_COLOUR = HexColor("#1A1A1A")
ORIGIN_PHRASE = "Built by neurodivergent minds, for neurodivergent people."
TRUST_FOOTER = "Disclosure guidance developed with BRAINS Trust safeguarding principles."


def _make_styles():
    h1 = ParagraphStyle(
        name="H1",
        fontName="Helvetica-Bold",
        fontSize=18,
        textColor=GOLD_DEEP,
        spaceAfter=12,
    )
    h2 = ParagraphStyle(
        name="H2",
        fontName="Helvetica-Bold",
        fontSize=14,
        textColor=GOLD_DEEP,
        spaceAfter=10,
        spaceBefore=14,
    )
    body = ParagraphStyle(
        name="Body",
        fontName="Helvetica",
        fontSize=11,
        textColor=BODY_COLOUR,
        leading=16,
    )
    meta = ParagraphStyle(
        name="Meta",
        fontName="Helvetica",
        fontSize=9,
        textColor=grey,
    )
    footer = ParagraphStyle(
        name="Footer",
        fontName="Helvetica",
        fontSize=9,
        textColor=grey,
        alignment=1,  # centre
    )
    return h1, h2, body, meta, footer


def render_coaching_report_pdf(
    out_path: Union[str, Path],
    title: str,
    resume_filename: str,
    skill_version: str,
    executive_summary: str,
    ats_status: str,
    ats_findings: str,
    bias_findings: str,
    next_steps: str,
    include_trust_footer: bool,
    brand_mark_path: Union[str, Path],
) -> Path:
    """Render a BRAINS-branded coaching report PDF.

    Parameters
    ----------
    out_path : path
        Where to write the PDF.
    title : str
    resume_filename : str
    skill_version : str
    executive_summary : str
    ats_status : str
    ats_findings : str
    bias_findings : str
    next_steps : str
    include_trust_footer : bool
        If True, render the BRAINS Trust safeguarding credit line above the standard footer.
        Used for disclosure worksheets.
    brand_mark_path : path
        Path to the BRAINS mark PNG to place top-left.
    """
    out_path = Path(out_path)
    brand_mark_path = Path(brand_mark_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    h1, h2, body, meta, footer = _make_styles()

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    story = []

    if brand_mark_path.exists():
        story.append(Image(str(brand_mark_path), width=1.2 * inch, height=0.5 * inch))
        story.append(Spacer(1, 12))

    story.append(Paragraph(title, h1))
    story.append(Paragraph(f"Resume reviewed: {resume_filename}", meta))
    story.append(Paragraph(f"BRAINS Resume Skill v{skill_version}", meta))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Summary", h2))
    story.append(Paragraph(executive_summary, body))

    story.append(Paragraph("ATS-safety findings", h2))
    story.append(Paragraph(f"Status: <b>{ats_status}</b>", body))
    story.append(Spacer(1, 6))
    for line in ats_findings.splitlines():
        if line.strip():
            story.append(Paragraph(line, body))

    story.append(Paragraph("ND-bias findings", h2))
    for line in bias_findings.splitlines():
        if line.strip():
            story.append(Paragraph(line, body))

    story.append(Paragraph("Recommended next steps", h2))
    for line in next_steps.splitlines():
        if line.strip():
            story.append(Paragraph(line, body))

    story.append(Spacer(1, 24))

    if include_trust_footer:
        story.append(Paragraph(TRUST_FOOTER, footer))
        story.append(Spacer(1, 6))

    story.append(Paragraph(ORIGIN_PHRASE, footer))

    doc.build(story)
    return out_path
