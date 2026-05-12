"""Cover-letter PDF generator.

Renders a clean business-letter PDF directly via reportlab. UNBRANDED.

Two templates:
  - formal-business (default): traditional letterhead, name in 14pt, full
    recipient block, "Sincerely," sign-off.
  - modern-clean: smaller letterhead block, more whitespace between paragraphs,
    less typographic weight — suited to tech/startup contexts.
"""
from pathlib import Path
from typing import Union

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer


BODY_COLOUR = HexColor("#1A1A1A")

VALID_TEMPLATES = ("formal-business", "modern-clean")


def _make_styles(name_size: int = 14, body_size: int = 11, paragraph_spacing: int = 10):
    name_style = ParagraphStyle(
        name="LetterName", fontName="Helvetica", fontSize=name_size,
        textColor=BODY_COLOUR, spaceAfter=2,
    )
    contact_style = ParagraphStyle(
        name="LetterContact", fontName="Helvetica", fontSize=10,
        textColor=BODY_COLOUR, spaceAfter=14,
    )
    body_style = ParagraphStyle(
        name="LetterBody", fontName="Helvetica", fontSize=body_size,
        textColor=BODY_COLOUR, leading=15, spaceAfter=paragraph_spacing,
    )
    return name_style, contact_style, body_style


def _render_formal_business(data: dict, story: list, styles):
    name_s, contact_s, body_s = styles
    story.append(Paragraph(data.get("candidate_name", ""), name_s))
    story.append(Paragraph(data.get("candidate_contact_line", ""), contact_s))
    story.append(Paragraph(data.get("letter_date", ""), body_s))

    for line in (
        data.get("recipient_name", ""),
        data.get("recipient_title", ""),
        data.get("recipient_company", ""),
    ):
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


def _render_modern_clean(data: dict, story: list, styles):
    """Smaller letterhead block, more whitespace, no formal recipient block."""
    name_s, contact_s, body_s = styles
    story.append(Paragraph(data.get("candidate_name", ""), name_s))
    story.append(Paragraph(data.get("candidate_contact_line", ""), contact_s))
    story.append(Spacer(1, 12))

    story.append(Paragraph(data.get("letter_date", ""), body_s))
    story.append(Spacer(1, 6))

    salutation = data.get("salutation", "Hiring Team")
    story.append(Paragraph(f"Hi {salutation},", body_s))
    story.append(Spacer(1, 6))

    for key in ("hook_paragraph", "fit_paragraph", "close_paragraph"):
        if data.get(key):
            story.append(Paragraph(data[key], body_s))
            story.append(Spacer(1, 4))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Best,", body_s))
    story.append(Spacer(1, 18))
    story.append(Paragraph(data.get("candidate_name", ""), body_s))


TEMPLATE_RENDERERS = {
    "formal-business": (_render_formal_business, {"name_size": 14, "body_size": 11, "paragraph_spacing": 10}),
    "modern-clean":    (_render_modern_clean,    {"name_size": 16, "body_size": 11, "paragraph_spacing": 12}),
}


def render_cover_letter_pdf(
    data: dict,
    out_path: Union[str, Path],
    template: str = "formal-business",
) -> Path:
    """Render a cover letter to PDF.

    template choices: formal-business (default), modern-clean.
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
        title=f"{data.get('candidate_name', 'Cover Letter')} - Cover Letter",
        author=data.get("candidate_name", ""),
    )
    story: list = []
    renderer(data, story, styles)

    doc.build(story)
    return out_path
