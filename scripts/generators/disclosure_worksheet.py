"""Render the disclosure worksheet — markdown + branded PDF.

A worksheet is rendered direct from a `DisclosureSession` + `Candidate`
pair. The markdown is for human readability and audit; the PDF is rendered
directly from the same structured data using the same brand chrome as
`coaching_report_to_pdf` (gold-deep headings, BRAINS mark, Trust footer).

Public API:
- render_markdown(session, candidate, skill_version) -> str
- render_pdf(session, candidate, out_path, *, skill_version, brand_mark_path) -> Path
- generate(session_id, *, output_root=None) -> tuple[Path, Path]
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Optional

from PIL import Image as PILImage
from reportlab.lib.colors import HexColor, grey
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from scripts.outputs.naming import new_uid, slugify
from scripts.tracker import disclosure as disclosure_db
from scripts.tracker.candidates import get_candidate
from scripts.tracker.models import Candidate, DisclosureSession


GOLD_DEEP = HexColor("#D99518")
BODY_COLOUR = HexColor("#1A1A1A")
ORIGIN_PHRASE = "Built by neurodivergent minds, for neurodivergent people."
TRUST_FOOTER = "Disclosure guidance developed with BRAINS Trust safeguarding principles."

_DEFAULT_SKILL_VERSION = "2.3.0"
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_TEMPLATE_PATH = _REPO_ROOT / "templates" / "disclosure_worksheet.md"
_DEFAULT_BRAND_MARK = _REPO_ROOT / "assets" / "brains-mark-light-bg.png"


_STRENGTH_HUMAN = {
    "non-disclosure": "non-disclosure",
    "neutral": "neutral signalling",
    "explicit": "explicit disclosure",
    "undecided": "undecided",
}


def _human_strength(landed: str) -> str:
    return _STRENGTH_HUMAN.get(landed, landed)


def _fmt_factor(value: Optional[str]) -> str:
    return value.strip() if value and value.strip() else "(not recorded)"


def _candidate_full_name(c: Candidate) -> str:
    return f"{c.first_name} {c.last_name}".strip()


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

def render_markdown(
    session: DisclosureSession,
    candidate: Candidate,
    skill_version: str = _DEFAULT_SKILL_VERSION,
) -> str:
    """Render the worksheet to markdown using the template."""
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")

    report_date = session.created_at[:10] if session.created_at else date.today().isoformat()

    target_employer_line = (
        f"**Target employer:** {session.target_employer}"
        if session.target_employer else ""
    )
    target_role_line = (
        f"**Target role:** {session.target_role}"
        if session.target_role else ""
    )

    notes_block = ""
    if session.notes and session.notes.strip():
        notes_block = (
            "\n---\n\n## Notes\n\n"
            f"{session.notes.strip()}\n"
        )

    substitutions = {
        "{{REPORT_DATE}}": report_date,
        "{{CANDIDATE_NAME}}": _candidate_full_name(candidate),
        "{{SKILL_VERSION}}": skill_version,
        "{{TARGET_EMPLOYER_LINE}}": target_employer_line,
        "{{TARGET_ROLE_LINE}}": target_role_line,
        "{{FACTOR_1}}": _fmt_factor(session.factor_1),
        "{{FACTOR_2}}": _fmt_factor(session.factor_2),
        "{{FACTOR_3}}": _fmt_factor(session.factor_3),
        "{{FACTOR_4}}": _fmt_factor(session.factor_4),
        "{{FACTOR_5}}": _fmt_factor(session.factor_5),
        "{{FACTOR_6}}": _fmt_factor(session.factor_6),
        "{{LANDED_STRENGTH_HUMAN}}": _human_strength(session.landed_strength),
        "{{NOTES_BLOCK}}": notes_block,
    }
    rendered = template
    for token, value in substitutions.items():
        rendered = rendered.replace(token, value)
    # Collapse runs of more than 2 blank lines that came from empty
    # optional-line substitutions (e.g. missing target employer + role).
    while "\n\n\n\n" in rendered:
        rendered = rendered.replace("\n\n\n\n", "\n\n\n")
    return rendered


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

def _make_styles():
    h1 = ParagraphStyle(
        name="DiscH1", fontName="Helvetica-Bold", fontSize=18,
        textColor=GOLD_DEEP, spaceAfter=12,
    )
    h2 = ParagraphStyle(
        name="DiscH2", fontName="Helvetica-Bold", fontSize=14,
        textColor=GOLD_DEEP, spaceAfter=10, spaceBefore=14,
    )
    body = ParagraphStyle(
        name="DiscBody", fontName="Helvetica", fontSize=11,
        textColor=BODY_COLOUR, leading=16, spaceAfter=8,
    )
    body_bold = ParagraphStyle(
        name="DiscBodyBold", fontName="Helvetica-Bold", fontSize=11,
        textColor=BODY_COLOUR, leading=16, spaceAfter=8,
    )
    meta = ParagraphStyle(
        name="DiscMeta", fontName="Helvetica", fontSize=9, textColor=grey,
    )
    quote = ParagraphStyle(
        name="DiscQuote", fontName="Helvetica-Oblique", fontSize=11,
        textColor=BODY_COLOUR, leading=16, spaceAfter=10,
        leftIndent=18, rightIndent=18,
    )
    footer = ParagraphStyle(
        name="DiscFooter", fontName="Helvetica", fontSize=9,
        textColor=grey, alignment=1,
    )
    return h1, h2, body, body_bold, meta, quote, footer


def _factor_table(session: DisclosureSession) -> Table:
    header = ["#", "Factor", "Your answer"]
    rows = [
        ("1", "Employer ND-affirming in concrete, formal-programme terms?", _fmt_factor(session.factor_1)),
        ("2", "Role disability-, accessibility-, or ND-affirming-adjacent?", _fmt_factor(session.factor_2)),
        ("3", "Channel screens for ND inclusion?", _fmt_factor(session.factor_3)),
        ("4", "Need accommodation at application stage?", _fmt_factor(session.factor_4)),
        ("5", "Values-driven to disclose regardless of bias risk?", _fmt_factor(session.factor_5)),
        ("6", "Professional advice received for this case?", _fmt_factor(session.factor_6)),
    ]
    cell_style = ParagraphStyle(
        name="DiscCell", fontName="Helvetica", fontSize=10,
        textColor=BODY_COLOUR, leading=13,
    )
    header_style = ParagraphStyle(
        name="DiscCellH", fontName="Helvetica-Bold", fontSize=10,
        textColor=BODY_COLOUR, leading=13,
    )
    data = [[Paragraph(c, header_style) for c in header]] + [
        [Paragraph(c, cell_style) for c in row] for row in rows
    ]
    table = Table(data, colWidths=[0.4 * inch, 3.3 * inch, 3.0 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#F5F0E5")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, grey),
        ("LINEBELOW", (0, 1), (-1, -1), 0.25, HexColor("#DDDDDD")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def render_pdf(
    session: DisclosureSession,
    candidate: Candidate,
    out_path: Path,
    *,
    skill_version: str = _DEFAULT_SKILL_VERSION,
    brand_mark_path: Optional[Path] = None,
) -> Path:
    """Render the worksheet PDF direct from the session + candidate."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    brand_mark_path = Path(brand_mark_path) if brand_mark_path else _DEFAULT_BRAND_MARK

    h1, h2, body, body_bold, meta, quote, footer = _make_styles()

    doc = SimpleDocTemplate(
        str(out_path), pagesize=letter,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
    )
    story = []

    if brand_mark_path.exists():
        with PILImage.open(brand_mark_path) as pil_img:
            natural_w, natural_h = pil_img.size
        target_height = 0.6 * inch
        target_width = target_height * (natural_w / natural_h)
        story.append(Image(str(brand_mark_path), width=target_width, height=target_height))
        story.append(Spacer(1, 12))

    # Header
    story.append(Paragraph("BRAINS Resume Skill — Disclosure Decision Worksheet", h1))
    report_date = session.created_at[:10] if session.created_at else date.today().isoformat()
    story.append(Paragraph(f"Prepared: {report_date}", meta))
    story.append(Paragraph(f"Candidate: {_candidate_full_name(candidate)}", meta))
    story.append(Paragraph(f"BRAINS Resume Skill v{skill_version}", meta))
    if session.target_employer:
        story.append(Paragraph(f"Target employer: {session.target_employer}", meta))
    if session.target_role:
        story.append(Paragraph(f"Target role: {session.target_role}", meta))
    story.append(Spacer(1, 14))

    # Boundary statements
    story.append(Paragraph("Boundary statements", h2))
    story.append(Paragraph(
        "This workflow does <b>not</b> provide individual legal advice. It does "
        "<b>not</b> diagnose any condition. It does <b>not</b> replace "
        "professional advice from an employment advocate, disability-rights "
        "lawyer, or clinician.",
        body,
    ))
    story.append(Paragraph(
        "This is general guidance, not legal or medical advice. For specific "
        "decisions about your application, accommodation, or disclosure, "
        "consult an employment advocate, disability-rights lawyer, or — where "
        "relevant — a clinician.",
        body,
    ))

    # Default position
    story.append(Paragraph("Default position", h2))
    story.append(Paragraph(
        "The starting point in this framework is <b>not to disclose "
        "neurodivergent identity on the resume itself.</b> This is not a "
        "statement that disclosure is wrong; it is a practical starting point "
        "grounded in three observations:",
        body,
    ))
    for bullet in (
        "Accommodations are protected separately from resume content in most "
        "jurisdictions; in many places you can request reasonable accommodation "
        "later without disclosing on the resume.",
        "Disclosure on a resume cannot be retracted. Once it is on a document, "
        "every reader of every version has access to it.",
        "Later-stage disclosure (interview, post-offer, post-acceptance) tends "
        "to carry stronger protections, though specifics vary significantly by "
        "jurisdiction.",
    ):
        story.append(Paragraph(f"• {bullet}", body))
    story.append(Paragraph(
        "The default holds unless the six factors below shift it.", body,
    ))

    # Six-factor answers
    story.append(Paragraph("Your six-factor answers", h2))
    story.append(_factor_table(session))
    story.append(Spacer(1, 12))

    # Landed strength
    story.append(Paragraph("Landed disclosure strength", h2))
    story.append(Paragraph(
        f"<b>You landed on: {_human_strength(session.landed_strength)}.</b> "
        "This is a position you recorded after walking through the framework "
        "— you can change it any time by running the workflow again, and the "
        "framework does not make the decision for you.",
        body,
    ))
    story.append(Paragraph("The three disclosure-strength definitions, for reference:", body))
    for label, defn in (
        ("Non-disclosure",
         "the resume contains no reference to neurodivergent identity, "
         "disability, or accessibility needs."),
        ("Neutral signalling",
         "language reflects ND-associated strengths or accessibility-aware "
         "professional experience without explicitly naming neurodivergent "
         "identity."),
        ("Explicit disclosure",
         "the resume or cover letter directly names neurodivergent identity "
         "as part of the professional narrative. Used with full awareness "
         "that it cannot be retracted."),
    ):
        story.append(Paragraph(f"• <b>{label}</b> — {defn}", body))

    # Optional notes
    if session.notes and session.notes.strip():
        story.append(Paragraph("Notes", h2))
        for paragraph in session.notes.strip().split("\n\n"):
            story.append(Paragraph(paragraph.strip().replace("\n", " "), body))

    # Talking points
    story.append(Paragraph("Talking points for downstream disclosure (reference)", h2))
    story.append(Paragraph(
        "If you go with non-disclosure or neutral signalling on the resume, "
        "the question of how to talk about identity at interview and after an "
        "offer still arises. These templates are starting points, not scripts.",
        body,
    ))
    story.append(Paragraph("At interview stage (illustrative):", body_bold))
    story.append(Paragraph(
        "\"I want to share something I think is relevant to how I work and how "
        "I'd like to set this conversation up for success. I'm "
        "[autistic / an ADHDer / neurodivergent — your framing]. That shapes "
        "how I process and communicate, and I do my best work when I have a "
        "moment to gather my thoughts before answering a complex question. "
        "Happy to say more if it's useful.\"",
        quote,
    ))
    story.append(Paragraph("After an offer (illustrative):", body_bold))
    story.append(Paragraph(
        "\"Thank you for the offer — I'm genuinely excited about this role. "
        "Before I formally accept I'd like to share something and, if "
        "appropriate, discuss whether any accommodations would be helpful. "
        "I'm [neurodivergent identity in your preferred terms]. I don't "
        "anticipate this affecting performance in the ways the role requires, "
        "but I want to be open about it and explore whether there's anything "
        "that would help me do my best work from the start.\"",
        quote,
    ))
    story.append(Paragraph("After acceptance — requesting an accommodation (illustrative):", body_bold))
    story.append(Paragraph(
        "\"I want to raise something as we set up how I'll be working. I'm "
        "[neurodivergent identity], and I've found that [specific, practical "
        "accommodation] makes a real difference to the quality and "
        "consistency of my output. I'd like to explore whether that's "
        "something we can put in place.\"",
        quote,
    ))

    # Recommended next steps
    story.append(Paragraph("Recommended next steps", h2))
    for i, step in enumerate((
        "Sit with your landed position for a day or two if helpful. It is "
        "reversible at any point in the future.",
        "Consider professional advice in your jurisdiction. A one-off "
        "consultation with a disability-rights lawyer or an employment-law "
        "advocate familiar with the applicable law strengthens the basis for "
        "the decision regardless of which strength you chose.",
        "Run the resume review and edit workflows next. The BRAINS Resume "
        "Skill will read this landed position and apply it consistently, "
        "surfacing what it changed so you can see and override.",
        "Keep a copy of this worksheet. Your decision is yours; this document "
        "is a record of the reasoning behind it, not an authority over it.",
    ), start=1):
        story.append(Paragraph(f"{i}. {step}", body))

    # Restated boundary
    story.append(Paragraph("Boundary statements (restated)", h2))
    story.append(Paragraph(
        "This workflow does <b>not</b> provide individual legal advice. It "
        "does <b>not</b> diagnose any condition. It does <b>not</b> replace "
        "professional advice from an employment advocate, disability-rights "
        "lawyer, or clinician.",
        body,
    ))

    story.append(Spacer(1, 24))
    story.append(Paragraph(TRUST_FOOTER, footer))
    story.append(Spacer(1, 6))
    story.append(Paragraph(ORIGIN_PHRASE, footer))

    doc.build(story)
    return out_path


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def _candidate_slug(c: Candidate) -> str:
    return slugify(f"{c.first_name}-{c.last_name}") or f"candidate-{c.id}"


def _resolve_output_root(output_root: Optional[Path]) -> Path:
    if output_root is not None:
        return Path(output_root)
    from scripts.outputs.io import get_outputs_root
    return get_outputs_root() / "disclosure"


def generate(
    session_id: int,
    *,
    output_root: Optional[Path] = None,
    skill_version: str = _DEFAULT_SKILL_VERSION,
    brand_mark_path: Optional[Path] = None,
) -> tuple[Path, Path]:
    """Generate worksheet markdown + PDF for a session.

    Assigns a new artifact_uid to the session if it doesn't already have
    one and persists it via disclosure.set_artifact_uid. Writes both files
    to <output_root>/<candidate-slug>/disclosure-<YYYY-MM-DD>-<uid>.{md,pdf}.

    Returns (markdown_path, pdf_path).
    """
    session = disclosure_db.get_session(session_id)
    if session is None:
        raise ValueError(f"No disclosure session with id={session_id}")
    candidate = get_candidate(session.candidate_id)
    if candidate is None:
        raise ValueError(
            f"Session {session_id} points at candidate {session.candidate_id}, "
            "which no longer exists."
        )

    artifact_uid = session.artifact_uid or new_uid()
    if not session.artifact_uid:
        disclosure_db.set_artifact_uid(session_id, artifact_uid)
        session = disclosure_db.get_session(session_id)  # refresh

    folder = _resolve_output_root(output_root) / _candidate_slug(candidate)
    folder.mkdir(parents=True, exist_ok=True)

    created_date = (
        datetime.fromisoformat(session.created_at.rstrip("Z")).date()
        if session.created_at else date.today()
    )
    stem = f"disclosure-{created_date.isoformat()}-{artifact_uid}"
    md_path = folder / f"{stem}.md"
    pdf_path = folder / f"{stem}.pdf"

    md_path.write_text(
        render_markdown(session, candidate, skill_version=skill_version),
        encoding="utf-8",
    )
    render_pdf(
        session, candidate, pdf_path,
        skill_version=skill_version,
        brand_mark_path=brand_mark_path,
    )
    return md_path, pdf_path
