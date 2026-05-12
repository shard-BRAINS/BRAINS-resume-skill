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

from PIL import Image as PILImage
from reportlab.lib.colors import HexColor, grey
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
        # Preserve the mark's natural aspect ratio: lock target height,
        # compute width from the source image's intrinsic dimensions.
        with PILImage.open(brand_mark_path) as pil_img:
            natural_w, natural_h = pil_img.size
        target_height = 0.6 * inch
        target_width = target_height * (natural_w / natural_h)
        story.append(Image(str(brand_mark_path), width=target_width, height=target_height))
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


import re


def _parse_markdown_report(md_text: str) -> dict:
    """Extract the known coaching-report sections from markdown source.

    Recognised level-1 heading: title (the first ``# `` line).
    Recognised level-2 headings: Summary, ATS-safety findings, ND-bias findings,
    Recommended next steps. The Status: line under ATS-safety findings is
    extracted separately when present.
    """
    title_match = re.search(r"^#\s+(.+)$", md_text, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "Coaching Report"

    metadata_lines = []
    for line in md_text.splitlines():
        if line.startswith("**Prepared:**") or line.startswith("**Resume reviewed:**") or line.startswith("**Reviewer:**"):
            metadata_lines.append(line)

    resume_filename = ""
    skill_version = ""
    for line in metadata_lines:
        if "Resume reviewed:" in line:
            resume_filename = line.split("Resume reviewed:**", 1)[-1].strip()
        if "Reviewer:" in line and "v" in line:
            v_match = re.search(r"v(\d+\.\d+\.\d+)", line)
            if v_match:
                skill_version = v_match.group(1)

    def _extract_section(label: str) -> str:
        pattern = rf"##\s+{re.escape(label)}\s*\n(.+?)(?=\n##\s+|\Z)"
        m = re.search(pattern, md_text, re.DOTALL)
        return m.group(1).strip() if m else ""

    summary = _extract_section("Summary")
    ats_block = _extract_section("ATS-safety findings")
    bias_block = _extract_section("ND-bias findings")
    next_steps = _extract_section("Recommended next steps")

    ats_status = "N/A"
    ats_status_match = re.search(r"\*\*Status:\*\*\s+(\S+)", ats_block)
    if ats_status_match:
        ats_status = ats_status_match.group(1)
        ats_block = re.sub(r"\*\*Status:\*\*\s+\S+\s*\n?", "", ats_block).strip()

    return {
        "title": title,
        "resume_filename": resume_filename or "(unspecified)",
        "skill_version": skill_version or "1.0.0",
        "executive_summary": summary or "(no summary provided)",
        "ats_status": ats_status,
        "ats_findings": ats_block or "No issues detected.",
        "bias_findings": bias_block or "No patterns detected.",
        "next_steps": next_steps or "(none)",
    }


def render_from_markdown(
    md_path: Union[str, Path],
    out_path: Union[str, Path],
    brand_mark_path: Union[str, Path],
    include_trust_footer: bool = False,
) -> Path:
    """Render a coaching report PDF from a markdown source file.

    The markdown file is the single source of truth; this avoids the
    structured-data-reconstruction step that has caused duplication bugs
    in workflow integrations.
    """
    md_path = Path(md_path)
    if not md_path.exists():
        raise FileNotFoundError(f"Markdown report not found: {md_path}")
    md_text = md_path.read_text(encoding="utf-8")
    parsed = _parse_markdown_report(md_text)
    return render_coaching_report_pdf(
        out_path=out_path,
        title=parsed["title"],
        resume_filename=parsed["resume_filename"],
        skill_version=parsed["skill_version"],
        executive_summary=parsed["executive_summary"],
        ats_status=parsed["ats_status"],
        ats_findings=parsed["ats_findings"],
        bias_findings=parsed["bias_findings"],
        next_steps=parsed["next_steps"],
        include_trust_footer=include_trust_footer,
        brand_mark_path=brand_mark_path,
    )
