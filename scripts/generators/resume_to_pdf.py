"""Resume PDF generator.

Renders an ATS-safe PDF directly from structured resume data using reportlab.
UNBRANDED — no BRAINS marks, no protected phrases, no Gold Deep accents.

Supports four templates: chronological (default), functional, hybrid, executive.
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

VALID_TEMPLATES = ("chronological", "functional", "hybrid", "executive")


def _make_styles(name_size: int = 22, section_size: int = 12, body_size: int = 11):
    name_style = ParagraphStyle(
        name="ResumeName", fontName="Helvetica", fontSize=name_size,
        textColor=BODY_COLOUR, spaceAfter=4,
    )
    contact_style = ParagraphStyle(
        name="ResumeContact", fontName="Helvetica", fontSize=10,
        textColor=MUTED, spaceAfter=14,
    )
    section_style = ParagraphStyle(
        name="ResumeSection", fontName="Helvetica-Bold", fontSize=section_size,
        textColor=BODY_COLOUR, spaceBefore=10, spaceAfter=6,
    )
    body_style = ParagraphStyle(
        name="ResumeBody", fontName="Helvetica", fontSize=body_size,
        textColor=BODY_COLOUR, leading=15,
    )
    return name_style, contact_style, section_style, body_style


def _render_chronological(data: dict, story: list, styles):
    name_s, contact_s, section_s, body_s = styles
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


def _render_functional(data: dict, story: list, styles):
    """Skills-led layout. Experience is minimised — titles + dates only.

    For users with career-changing or gap-friendly framing needs. Note the
    recruiter-skepticism tradeoff documented in references/template-selection.md.
    """
    name_s, contact_s, section_s, body_s = styles
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


def _render_hybrid(data: dict, story: list, styles):
    """Skills summary block first, then full reverse-chronological experience.

    Recommended for career pivots with relevant transferable skills.
    """
    name_s, contact_s, section_s, body_s = styles
    story.append(Paragraph(data.get("candidate_name", ""), name_s))
    story.append(Paragraph(data.get("candidate_contact_line", ""), contact_s))
    story.append(Paragraph("Summary", section_s))
    story.append(Paragraph(data.get("summary", ""), body_s))
    story.append(Paragraph("Key Skills", section_s))
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


def _render_executive(data: dict, story: list, styles):
    """Executive layout: achievement-led summary, larger name heading,
    optional 2-page allowance handled implicitly by reportlab page flow.
    """
    name_s, contact_s, section_s, body_s = styles
    story.append(Paragraph(data.get("candidate_name", ""), name_s))
    story.append(Paragraph(data.get("candidate_contact_line", ""), contact_s))
    story.append(Paragraph("Executive Summary", section_s))
    story.append(Paragraph(data.get("summary", ""), body_s))
    story.append(Paragraph("Career Highlights", section_s))
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


TEMPLATE_RENDERERS = {
    "chronological": (_render_chronological, {"name_size": 22, "section_size": 12, "body_size": 11}),
    "functional":    (_render_functional,    {"name_size": 22, "section_size": 12, "body_size": 11}),
    "hybrid":        (_render_hybrid,        {"name_size": 22, "section_size": 12, "body_size": 11}),
    "executive":     (_render_executive,     {"name_size": 24, "section_size": 13, "body_size": 11}),
}


def render_resume_pdf(
    data: dict,
    out_path: Union[str, Path],
    template: str = "chronological",
) -> Path:
    """Render a structured resume dict to an ATS-safe PDF.

    template choices: chronological (default), functional, hybrid, executive.
    """
    if template not in VALID_TEMPLATES:
        raise ValueError(
            f"Unknown template {template!r}. Valid options: {', '.join(VALID_TEMPLATES)}"
        )

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    renderer, style_opts = TEMPLATE_RENDERERS[template]
    styles = _make_styles(**style_opts)

    doc = SimpleDocTemplate(
        str(out_path), pagesize=letter,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        title=f"{data.get('candidate_name', 'Resume')} - Resume",
        author=data.get("candidate_name", ""),
    )
    story: list = []
    renderer(data, story, styles)

    doc.build(story)
    return out_path
