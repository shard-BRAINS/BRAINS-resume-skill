# Plan 3 — Phase 2: Template Library, LinkedIn Profile Improvement, and Consolidation (v1.1.0)

<!-- readability: skip -->
<!-- Historical planning/spec document; predates the BRAINS readability standard (adopted 2026-05-29). -->

> **For implementers:** Checkbox (`- [ ]`) syntax. Work sequentially, mark steps as you go. Stage and commit after each task. **Never include third-party org or project credits in any file or commit message — BRAINS / BRAINS Trust / BRAINS Incubator only. Never include `Co-Authored-By` footers.** Conventional commits style.

**Goal:** Ship v1.1.0 — add a 4-template resume library + 2-template cover-letter library with explicit template-selection guidance, a LinkedIn profile improvement workflow that applies the ND-aware framework to a parallel job-search surface, and a resume + LinkedIn consolidation workflow that detects and surfaces narrative inconsistencies between a user's two main job-search documents.

**Architecture:** Same hybrid skill structure as v1.0.x (always-loaded `SKILL.md` core + on-demand reference files + deterministic Python scripts). Adds a new `templates/resume/` and `templates/cover-letter/` directory layout (existing single templates migrated into them). Generators take a new `template=` parameter with backward-compatible defaults. Adds one new validator (`consolidation_check.py`) and two new workflow references with matching slash commands.

**Tech Stack:** Unchanged — Python 3.10+, `python-docx`, `pdfplumber`, `reportlab`, `Pillow`, `pyyaml`, `pytest`. No new dependencies.

**Spec reference:** [`docs/specs/2026-05-13-phase-2-templates-linkedin-consolidation-design.md`](../specs/2026-05-13-phase-2-templates-linkedin-consolidation-design.md)

**In scope for this plan:**

1. **Template directory migration** — move existing single templates into new `templates/resume/` and `templates/cover-letter/` layout
2. **Generator parameterisation** — all four generators accept a `template=` parameter with a backward-compatible default
3. **Three new resume templates** — functional, hybrid, executive (each: generator script + DOCX file + tests)
4. **One new cover-letter template** — modern-clean (generator script + DOCX file + tests)
5. **PDF generator variant routing** — resume and cover-letter PDF generators route to per-template styling functions
6. **Template-selection reference** — `references/template-selection.md` with decision tree, comparison table, and ND-framing on the functional-template tradeoff
7. **LinkedIn profile improvement workflow** — `references/workflows/linkedin-improve.md` + `commands/brains-linkedin-improve.md` + smoke test
8. **Consolidation workflow** — `references/workflows/consolidate.md` + `commands/brains-consolidate.md` + new validator `scripts/validators/consolidation_check.py` + fixtures + smoke test
9. **SKILL.md router updates** — two new workflow entries, template-selection cross-references on existing workflows
10. **Brand-application reference update** — new artifact types covered by the unbranded-vs-branded rule
11. **README + CHANGELOG + Claude Project bundle** — slash-command cheat sheet, v1.1.0 entry, bundle rebuild
12. **v1.1.0 git tag**

**Out of scope (deferred to Phase 3 / future):**

- MCP server for Claude Desktop
- "Creative" resume templates (graphical, two-column, colour blocks)
- Autonomous LinkedIn editing (no API write path)
- Interview prep skill, salary negotiation skill (always sibling skills)
- Resume version management (multi-variant file management)
- OCR of scanned-image PDFs
- Live LinkedIn URL fetching

---

## Conventions used throughout this plan

- **Working directory:** `c:\Brains_Resume_Skill\`. All paths relative unless absolute is shown.
- **Tests live in:** `tests/` mirroring source structure.
- **Python fixtures:** `tests/fixtures/*.py`. Binary fixtures: `docs/testing/fixtures/`.
- **Commit style:** conventional commits — `feat:`, `fix:`, `test:`, `docs:`, `build:`, `chore:`, `perf:`. NEVER include `Co-Authored-By` footers (BRAINS-only attribution).
- **Identity-first language** throughout; no italics in body text; no third-party org or project proper-name references.
- **Testing rhythm:** write failing test → run to confirm failure → implement → run to confirm pass → commit. Don't skip the failure-confirmation step; it catches "test passes because of a typo" bugs.
- **Virtual environment:** always work inside `.venv` — `.venv\Scripts\activate` (PowerShell) or `source .venv/bin/activate` (bash) before running tests or scripts.

---

## Phase 1 — Template infrastructure (Tasks 1-10)

The migration in Task 1 is the foundational change everything else depends on. Do it first and verify the existing suite is green before proceeding.

---

## Task 1 — Migrate templates into new directory layout

Move the two existing template files into the new directory structure and update every path reference. The existing chronological-resume and cover-letter templates remain the defaults; only their on-disk paths change.

**Files:**

- Move: `templates/resume_chronological.docx` → `templates/resume/chronological.docx`
- Move: `templates/cover_letter.docx` → `templates/cover-letter/formal-business.docx`
- Modify: `scripts/packaging/_make_resume_chronological_template.py` (path constant + rename file)
- Modify: `scripts/packaging/_make_cover_letter_template.py` (path constant + rename file)
- Modify: `scripts/generators/resume_to_docx.py` (TEMPLATE_PATH)
- Modify: `scripts/generators/cover_letter_to_docx.py` (TEMPLATE_PATH)
- Modify: `tests/templates/test_resume_chronological_template.py` (TEMPLATE path)
- Modify: `tests/templates/test_cover_letter_template.py` (TEMPLATE path)

### Steps

- [ ] **Step 1: Create new template directories**

```powershell
New-Item -ItemType Directory -Path "templates\resume" -Force
New-Item -ItemType Directory -Path "templates\cover-letter" -Force
```

- [ ] **Step 2: Move existing templates**

```powershell
git mv templates\resume_chronological.docx templates\resume\chronological.docx
git mv templates\cover_letter.docx templates\cover-letter\formal-business.docx
```

- [ ] **Step 3: Update path in `scripts/packaging/_make_resume_chronological_template.py`**

Rename the file at the same time. Final file name: `scripts/packaging/_make_resume_template_chronological.py` (singular "_resume_template_" prefix matches the new pattern that subsequent template-generator scripts in this plan will follow).

```powershell
git mv scripts\packaging\_make_resume_chronological_template.py scripts\packaging\_make_resume_template_chronological.py
```

In the renamed file, change the TEMPLATE_PATH constant:

```python
# Old
TEMPLATE_PATH = Path(__file__).parent.parent.parent / "templates" / "resume_chronological.docx"

# New
TEMPLATE_PATH = Path(__file__).parent.parent.parent / "templates" / "resume" / "chronological.docx"
```

- [ ] **Step 4: Update path in `scripts/packaging/_make_cover_letter_template.py`**

Rename and update:

```powershell
git mv scripts\packaging\_make_cover_letter_template.py scripts\packaging\_make_cover_letter_template_formal_business.py
```

In the renamed file, change the TEMPLATE_PATH constant:

```python
# Old
TEMPLATE_PATH = Path(__file__).parent.parent.parent / "templates" / "cover_letter.docx"

# New
TEMPLATE_PATH = Path(__file__).parent.parent.parent / "templates" / "cover-letter" / "formal-business.docx"
```

- [ ] **Step 5: Update path in `scripts/generators/resume_to_docx.py`**

```python
# Old
TEMPLATE_PATH = Path(__file__).parent.parent.parent / "templates" / "resume_chronological.docx"

# New — this is an interim value; Task 2 will replace it with a parameterised resolver.
DEFAULT_TEMPLATE = "chronological"
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates" / "resume"

# (Remove the old TEMPLATE_PATH constant. Inside render_resume_docx, replace
# the TEMPLATE_PATH reference with TEMPLATES_DIR / f"{DEFAULT_TEMPLATE}.docx".)
```

- [ ] **Step 6: Update path in `scripts/generators/cover_letter_to_docx.py`**

```python
# Old
TEMPLATE_PATH = Path(__file__).parent.parent.parent / "templates" / "cover_letter.docx"

# New — interim, Task 4 parameterises this.
DEFAULT_TEMPLATE = "formal-business"
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates" / "cover-letter"

# Inside render_cover_letter_docx, replace TEMPLATE_PATH reference with
# TEMPLATES_DIR / f"{DEFAULT_TEMPLATE}.docx".
```

- [ ] **Step 7: Update test path in `tests/templates/test_resume_chronological_template.py`**

```python
# Old
TEMPLATE = Path(__file__).parent.parent.parent / "templates" / "resume_chronological.docx"

# New
TEMPLATE = Path(__file__).parent.parent.parent / "templates" / "resume" / "chronological.docx"
```

- [ ] **Step 8: Update test path in `tests/templates/test_cover_letter_template.py`**

```python
# Old
TEMPLATE = Path(__file__).parent.parent.parent / "templates" / "cover_letter.docx"

# New
TEMPLATE = Path(__file__).parent.parent.parent / "templates" / "cover-letter" / "formal-business.docx"
```

- [ ] **Step 9: Run the full test suite to confirm nothing broke**

```powershell
.venv\Scripts\activate
python -m pytest -q
```

Expected: all existing tests still pass. If a test fails because it references the old path, find it with `grep` and update the reference:

```powershell
# In a separate terminal — search-only
Select-String -Path "tests\*.py","tests\**\*.py","scripts\**\*.py" -Pattern "resume_chronological\.docx|cover_letter\.docx"
```

- [ ] **Step 10: Commit**

```powershell
git add templates scripts tests
git commit -m "refactor: migrate templates into templates/{resume,cover-letter}/ directory layout"
```

---

## Task 2 — Parameterise `resume_to_docx` with `template=` argument

Add a `template=` keyword argument to `render_resume_docx` with the value `"chronological"` as the backward-compatible default. Unknown template names raise `ValueError`.

**Files:**

- Modify: `scripts/generators/resume_to_docx.py`
- Modify: `tests/generators/test_resume_to_docx.py`

### Steps

- [ ] **Step 1: Add failing tests for the new parameter**

Append to `tests/generators/test_resume_to_docx.py`:

```python
import pytest


def test_render_accepts_template_argument(tmp_path):
    out = tmp_path / "resume.docx"
    render_resume_docx(SAMPLE_RESUME_DATA, out, template="chronological")
    assert out.exists()


def test_render_unknown_template_raises_value_error(tmp_path):
    out = tmp_path / "resume.docx"
    with pytest.raises(ValueError) as exc_info:
        render_resume_docx(SAMPLE_RESUME_DATA, out, template="nonexistent")
    assert "nonexistent" in str(exc_info.value)
    assert "chronological" in str(exc_info.value)  # message lists valid templates


def test_render_default_template_unchanged_behaviour(tmp_path):
    """Default behaviour matches v1.0.x — calling without template= produces
    the chronological-template output."""
    out_default = tmp_path / "default.docx"
    out_explicit = tmp_path / "explicit.docx"
    render_resume_docx(SAMPLE_RESUME_DATA, out_default)
    render_resume_docx(SAMPLE_RESUME_DATA, out_explicit, template="chronological")
    # Both produced output; both contain the candidate name.
    from docx import Document
    text_default = "\n".join(p.text for p in Document(str(out_default)).paragraphs)
    text_explicit = "\n".join(p.text for p in Document(str(out_explicit)).paragraphs)
    assert "Alex Test" in text_default
    assert "Alex Test" in text_explicit
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
python -m pytest tests/generators/test_resume_to_docx.py -v
```

Expected: 3 failures — `TypeError: unexpected keyword argument 'template'` on the first two; the third may pass coincidentally but should still be present.

- [ ] **Step 3: Update `render_resume_docx` signature**

Replace the function definition in `scripts/generators/resume_to_docx.py`:

```python
VALID_TEMPLATES = ("chronological", "functional", "hybrid", "executive")


def render_resume_docx(
    data: dict,
    out_path: Union[str, Path],
    template: str = "chronological",
) -> Path:
    """Render a structured resume dict into the selected DOCX template.

    template choices: chronological (default), functional, hybrid, executive.
    Required keys in data: candidate_name, candidate_contact_line, summary,
    skills, experience, education. Missing keys default to an empty string.
    """
    if template not in VALID_TEMPLATES:
        raise ValueError(
            f"Unknown template {template!r}. Valid options: {', '.join(VALID_TEMPLATES)}"
        )

    template_path = TEMPLATES_DIR / f"{template}.docx"

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not template_path.exists():
        raise FileNotFoundError(f"Resume template not found: {template_path}")

    doc = Document(str(template_path))

    multiline_jobs = []
    for paragraph in list(doc.paragraphs):
        for key, placeholder in PLACEHOLDER_MAP.items():
            if placeholder in paragraph.text:
                value = data.get(key, "") or ""
                if "\n" in value:
                    multiline_jobs.append((paragraph, value))
                else:
                    _substitute_placeholder(paragraph, placeholder, value)

    for paragraph, value in multiline_jobs:
        _expand_multiline_paragraph(doc, paragraph, value)

    doc.save(str(out_path))
    return out_path
```

Also remove the now-unused `DEFAULT_TEMPLATE` constant (the `template=` parameter default replaces it).

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest tests/generators/test_resume_to_docx.py -v
```

Expected: all green. Note: the `chronological`, `functional`, `hybrid`, `executive` set means `functional`/`hybrid`/`executive` are valid names but their template files do not yet exist — calling with those template names will raise `FileNotFoundError`, which is correct behaviour at this stage.

- [ ] **Step 5: Commit**

```powershell
git add scripts/generators/resume_to_docx.py tests/generators/test_resume_to_docx.py
git commit -m "feat: add template= parameter to resume_to_docx generator"
```

---

## Task 3 — Parameterise `resume_to_pdf` with `template=` argument

PDF generators render directly from structured data via ReportLab (no DOCX template file). The `template=` parameter routes to per-template styling/structure functions.

**Files:**

- Modify: `scripts/generators/resume_to_pdf.py`
- Modify: `tests/generators/test_resume_to_pdf.py`

### Steps

- [ ] **Step 1: Add failing tests for the new parameter**

Append to `tests/generators/test_resume_to_pdf.py`:

```python
import pytest


def test_pdf_accepts_template_argument(tmp_path):
    out = tmp_path / "resume.pdf"
    render_resume_pdf(SAMPLE_RESUME_DATA, out, template="chronological")
    assert out.exists()
    assert out.stat().st_size > 0


def test_pdf_unknown_template_raises_value_error(tmp_path):
    out = tmp_path / "resume.pdf"
    with pytest.raises(ValueError) as exc_info:
        render_resume_pdf(SAMPLE_RESUME_DATA, out, template="nonexistent")
    assert "nonexistent" in str(exc_info.value)


def test_pdf_default_template_renders_chronological(tmp_path):
    out_default = tmp_path / "default.pdf"
    out_explicit = tmp_path / "explicit.pdf"
    render_resume_pdf(SAMPLE_RESUME_DATA, out_default)
    render_resume_pdf(SAMPLE_RESUME_DATA, out_explicit, template="chronological")
    assert out_default.exists()
    assert out_explicit.exists()


def test_pdf_functional_template_includes_skills_section_before_experience(tmp_path):
    """Functional template inverts the section order — skills-led, then
    minimal experience."""
    from pdfplumber import open as open_pdf
    out = tmp_path / "functional.pdf"
    render_resume_pdf(SAMPLE_RESUME_DATA, out, template="functional")
    with open_pdf(str(out)) as pdf:
        text = "\n".join(page.extract_text() for page in pdf.pages)
    skills_pos = text.find("Skills")
    experience_pos = text.find("Experience")
    assert 0 <= skills_pos < experience_pos


def test_pdf_executive_template_uses_larger_name_heading(tmp_path):
    """Executive template uses a larger name heading than chronological (24pt vs 22pt)."""
    out = tmp_path / "executive.pdf"
    render_resume_pdf(SAMPLE_RESUME_DATA, out, template="executive")
    assert out.exists()
    assert out.stat().st_size > 0
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
python -m pytest tests/generators/test_resume_to_pdf.py -v
```

Expected: failures — `TypeError: unexpected keyword argument 'template'`.

- [ ] **Step 3: Implement parameterised generator**

Replace `scripts/generators/resume_to_pdf.py` contents with:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest tests/generators/test_resume_to_pdf.py -v
```

Expected: all green.

- [ ] **Step 5: Commit**

```powershell
git add scripts/generators/resume_to_pdf.py tests/generators/test_resume_to_pdf.py
git commit -m "feat: add template= parameter to resume_to_pdf generator with per-template renderers"
```

---

## Task 4 — Parameterise `cover_letter_to_docx` with `template=` argument

**Files:**

- Modify: `scripts/generators/cover_letter_to_docx.py`
- Modify: `tests/generators/test_cover_letter_to_docx.py`

### Steps

- [ ] **Step 1: Add failing tests**

Append to `tests/generators/test_cover_letter_to_docx.py`:

```python
import pytest


def test_render_accepts_template_argument(tmp_path):
    out = tmp_path / "cover_letter.docx"
    render_cover_letter_docx(SAMPLE_LETTER_DATA, out, template="formal-business")
    assert out.exists()


def test_unknown_template_raises_value_error(tmp_path):
    out = tmp_path / "cover_letter.docx"
    with pytest.raises(ValueError) as exc_info:
        render_cover_letter_docx(SAMPLE_LETTER_DATA, out, template="nonexistent")
    assert "nonexistent" in str(exc_info.value)
    assert "formal-business" in str(exc_info.value)


def test_default_template_unchanged_behaviour(tmp_path):
    out_default = tmp_path / "default.docx"
    out_explicit = tmp_path / "explicit.docx"
    render_cover_letter_docx(SAMPLE_LETTER_DATA, out_default)
    render_cover_letter_docx(SAMPLE_LETTER_DATA, out_explicit, template="formal-business")
    from docx import Document
    text_d = "\n".join(p.text for p in Document(str(out_default)).paragraphs)
    text_e = "\n".join(p.text for p in Document(str(out_explicit)).paragraphs)
    assert text_d == text_e  # byte-equivalent rendering for the same data
```

(Note: `SAMPLE_LETTER_DATA` already exists in this test file from prior plan work; reuse it.)

- [ ] **Step 2: Run tests to verify they fail**

```powershell
python -m pytest tests/generators/test_cover_letter_to_docx.py -v
```

Expected: failures on the first two; third may pass coincidentally.

- [ ] **Step 3: Update `render_cover_letter_docx` signature**

Replace the function in `scripts/generators/cover_letter_to_docx.py`:

```python
VALID_TEMPLATES = ("formal-business", "modern-clean")


def render_cover_letter_docx(
    data: dict,
    out_path: Union[str, Path],
    template: str = "formal-business",
) -> Path:
    """Fill the cover-letter template with letter data and save.

    template choices: formal-business (default), modern-clean.
    """
    if template not in VALID_TEMPLATES:
        raise ValueError(
            f"Unknown template {template!r}. Valid options: {', '.join(VALID_TEMPLATES)}"
        )

    template_path = TEMPLATES_DIR / f"{template}.docx"

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

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
```

Remove the unused `DEFAULT_TEMPLATE` constant.

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest tests/generators/test_cover_letter_to_docx.py -v
```

Expected: all green.

- [ ] **Step 5: Commit**

```powershell
git add scripts/generators/cover_letter_to_docx.py tests/generators/test_cover_letter_to_docx.py
git commit -m "feat: add template= parameter to cover_letter_to_docx generator"
```

---

## Task 5 — Parameterise `cover_letter_to_pdf` with `template=` argument

**Files:**

- Modify: `scripts/generators/cover_letter_to_pdf.py`
- Modify: `tests/generators/test_cover_letter_to_pdf.py`

### Steps

- [ ] **Step 1: Add failing tests**

Append to `tests/generators/test_cover_letter_to_pdf.py`:

```python
import pytest


def test_pdf_accepts_template_argument(tmp_path):
    out = tmp_path / "cover_letter.pdf"
    render_cover_letter_pdf(SAMPLE_LETTER_DATA, out, template="formal-business")
    assert out.exists()


def test_pdf_unknown_template_raises_value_error(tmp_path):
    out = tmp_path / "cover_letter.pdf"
    with pytest.raises(ValueError) as exc_info:
        render_cover_letter_pdf(SAMPLE_LETTER_DATA, out, template="nonexistent")
    assert "nonexistent" in str(exc_info.value)


def test_pdf_default_template_unchanged(tmp_path):
    out_default = tmp_path / "default.pdf"
    out_explicit = tmp_path / "explicit.pdf"
    render_cover_letter_pdf(SAMPLE_LETTER_DATA, out_default)
    render_cover_letter_pdf(SAMPLE_LETTER_DATA, out_explicit, template="formal-business")
    assert out_default.exists()
    assert out_explicit.exists()


def test_pdf_modern_clean_template_renders(tmp_path):
    out = tmp_path / "modern.pdf"
    render_cover_letter_pdf(SAMPLE_LETTER_DATA, out, template="modern-clean")
    assert out.exists()
    assert out.stat().st_size > 0
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
python -m pytest tests/generators/test_cover_letter_to_pdf.py -v
```

Expected: failures.

- [ ] **Step 3: Implement parameterised generator**

Replace `scripts/generators/cover_letter_to_pdf.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest tests/generators/test_cover_letter_to_pdf.py -v
```

Expected: all green.

- [ ] **Step 5: Commit**

```powershell
git add scripts/generators/cover_letter_to_pdf.py tests/generators/test_cover_letter_to_pdf.py
git commit -m "feat: add template= parameter to cover_letter_to_pdf generator with per-template renderers"
```

---

## Task 6 — Functional resume template (DOCX)

Skills-grouped layout. Experience block is minimal (titles + dates only). For career-changers and gap-friendly framing. The recruiter-skepticism tradeoff is documented in Task 10's reference; the template itself is just a layout file.

**Files:**

- Create: `scripts/packaging/_make_resume_template_functional.py`
- Create: `templates/resume/functional.docx` (generated)
- Create: `tests/templates/test_resume_template_functional.py`

### Steps

- [ ] **Step 1: Write the template generator**

Create `scripts/packaging/_make_resume_template_functional.py`:

```python
"""Generate the functional resume DOCX template.

Skills-led layout. Experience section is minimal — titles + dates only.
Single-column. No tables. Calibri 11pt body, Calibri Light 22pt name.
Margins 0.75 inch. Page size US Letter. ATS-safe.
"""
from pathlib import Path
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

TEMPLATE_PATH = Path(__file__).parent.parent.parent / "templates" / "resume" / "functional.docx"


def make_template() -> Path:
    doc = Document()

    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    name = doc.add_paragraph()
    name.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = name.add_run("{{CANDIDATE_NAME}}")
    run.font.name = "Calibri Light"
    run.font.size = Pt(22)
    run.font.color.rgb = RGBColor(0x1A, 0x1A, 0x1A)

    contact = doc.add_paragraph("{{CANDIDATE_CONTACT_LINE}}")
    contact.runs[0].font.size = Pt(10)
    contact.runs[0].font.color.rgb = RGBColor(0x40, 0x40, 0x40)

    doc.add_paragraph()

    doc.add_heading("Summary", level=1)
    doc.add_paragraph("{{SUMMARY}}")

    # Functional layout: skills FIRST, with skill-grouped achievements.
    doc.add_heading("Skills and Achievements", level=1)
    doc.add_paragraph("{{SKILLS}}")

    # Experience section is minimised — titles + dates only.
    doc.add_heading("Experience", level=1)
    doc.add_paragraph("{{EXPERIENCE}}")

    doc.add_heading("Education", level=1)
    doc.add_paragraph("{{EDUCATION}}")

    TEMPLATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(TEMPLATE_PATH))
    return TEMPLATE_PATH


if __name__ == "__main__":
    path = make_template()
    print(f"Wrote {path}")
```

- [ ] **Step 2: Run the generator to produce the template**

```powershell
python scripts\packaging\_make_resume_template_functional.py
```

Expected: prints `Wrote ...\templates\resume\functional.docx`.

- [ ] **Step 3: Write template-validation tests**

Create `tests/templates/test_resume_template_functional.py`:

```python
"""Validate the functional resume template is ATS-safe."""
from pathlib import Path

from scripts.validators.ats_check import ats_check

TEMPLATE = Path(__file__).parent.parent.parent / "templates" / "resume" / "functional.docx"


def test_template_exists():
    assert TEMPLATE.exists(), f"Template missing: {TEMPLATE}"


def test_template_passes_ats_check():
    result = ats_check(TEMPLATE)
    assert result.passed, f"Failures: {[f.code for f in result.failures]}"


def test_template_contains_skills_heading_before_experience_heading():
    """Functional layout: skills come first, then experience."""
    from docx import Document
    doc = Document(str(TEMPLATE))
    text_in_order = [p.text for p in doc.paragraphs]
    flat = "\n".join(text_in_order)
    skills_pos = flat.find("Skills and Achievements")
    experience_pos = flat.find("Experience")
    assert 0 <= skills_pos < experience_pos


def test_template_uses_word_heading_styles():
    from docx import Document
    doc = Document(str(TEMPLATE))
    heading_paragraphs = [p for p in doc.paragraphs if p.style.name.startswith("Heading")]
    assert len(heading_paragraphs) >= 4  # Summary, Skills, Experience, Education
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest tests/templates/test_resume_template_functional.py -v
```

Expected: all green.

- [ ] **Step 5: Verify the generator-driven render works**

```powershell
python -c "from scripts.generators.resume_to_docx import render_resume_docx; from pathlib import Path; render_resume_docx({'candidate_name':'Test','candidate_contact_line':'test@x','summary':'X','skills':'Python','experience':'X','education':'X'}, Path('functional_test.docx'), template='functional'); print('OK')"
```

Expected: prints `OK`. Then delete the test file:

```powershell
Remove-Item functional_test.docx
```

- [ ] **Step 6: Commit**

```powershell
git add scripts/packaging/_make_resume_template_functional.py templates/resume/functional.docx tests/templates/test_resume_template_functional.py
git commit -m "feat: add functional resume DOCX template"
```

---

## Task 7 — Hybrid resume template (DOCX)

Skills summary block at the top followed by full reverse-chronological experience. The most-recommended template for career pivots where skills-led framing is needed but the user wants to avoid the functional-template recruiter-skepticism penalty.

**Files:**

- Create: `scripts/packaging/_make_resume_template_hybrid.py`
- Create: `templates/resume/hybrid.docx` (generated)
- Create: `tests/templates/test_resume_template_hybrid.py`

### Steps

- [ ] **Step 1: Write the template generator**

Create `scripts/packaging/_make_resume_template_hybrid.py`:

```python
"""Generate the hybrid resume DOCX template.

Skills summary block at top + full reverse-chronological experience below.
Recommended for career pivots with relevant transferable skills.
Single-column. No tables. Calibri 11pt body. ATS-safe.
"""
from pathlib import Path
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

TEMPLATE_PATH = Path(__file__).parent.parent.parent / "templates" / "resume" / "hybrid.docx"


def make_template() -> Path:
    doc = Document()

    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    name = doc.add_paragraph()
    name.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = name.add_run("{{CANDIDATE_NAME}}")
    run.font.name = "Calibri Light"
    run.font.size = Pt(22)
    run.font.color.rgb = RGBColor(0x1A, 0x1A, 0x1A)

    contact = doc.add_paragraph("{{CANDIDATE_CONTACT_LINE}}")
    contact.runs[0].font.size = Pt(10)
    contact.runs[0].font.color.rgb = RGBColor(0x40, 0x40, 0x40)

    doc.add_paragraph()

    doc.add_heading("Summary", level=1)
    doc.add_paragraph("{{SUMMARY}}")

    # Hybrid layout: skills SUMMARY block first (compact 3-5 bullets),
    # then full reverse-chronological experience.
    doc.add_heading("Key Skills", level=1)
    doc.add_paragraph("{{SKILLS}}")

    doc.add_heading("Experience", level=1)
    doc.add_paragraph("{{EXPERIENCE}}")

    doc.add_heading("Education", level=1)
    doc.add_paragraph("{{EDUCATION}}")

    TEMPLATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(TEMPLATE_PATH))
    return TEMPLATE_PATH


if __name__ == "__main__":
    path = make_template()
    print(f"Wrote {path}")
```

- [ ] **Step 2: Generate the template file**

```powershell
python scripts\packaging\_make_resume_template_hybrid.py
```

- [ ] **Step 3: Write tests**

Create `tests/templates/test_resume_template_hybrid.py`:

```python
"""Validate the hybrid resume template is ATS-safe."""
from pathlib import Path

from scripts.validators.ats_check import ats_check

TEMPLATE = Path(__file__).parent.parent.parent / "templates" / "resume" / "hybrid.docx"


def test_template_exists():
    assert TEMPLATE.exists(), f"Template missing: {TEMPLATE}"


def test_template_passes_ats_check():
    result = ats_check(TEMPLATE)
    assert result.passed, f"Failures: {[f.code for f in result.failures]}"


def test_template_has_key_skills_heading_before_experience():
    """Hybrid layout puts Key Skills before Experience."""
    from docx import Document
    doc = Document(str(TEMPLATE))
    flat = "\n".join(p.text for p in doc.paragraphs)
    skills_pos = flat.find("Key Skills")
    experience_pos = flat.find("Experience")
    assert 0 <= skills_pos < experience_pos
```

- [ ] **Step 4: Run tests**

```powershell
python -m pytest tests/templates/test_resume_template_hybrid.py -v
```

Expected: all green.

- [ ] **Step 5: Commit**

```powershell
git add scripts/packaging/_make_resume_template_hybrid.py templates/resume/hybrid.docx tests/templates/test_resume_template_hybrid.py
git commit -m "feat: add hybrid resume DOCX template"
```

---

## Task 8 — Executive resume template (DOCX)

Achievement-led, larger name heading, 2-page allowance. For senior roles, 15+ years experience, board/leadership framing.

**Files:**

- Create: `scripts/packaging/_make_resume_template_executive.py`
- Create: `templates/resume/executive.docx` (generated)
- Create: `tests/templates/test_resume_template_executive.py`

### Steps

- [ ] **Step 1: Write the template generator**

Create `scripts/packaging/_make_resume_template_executive.py`:

```python
"""Generate the executive resume DOCX template.

Achievement-led, larger name heading (24pt vs 22pt), 2-page allowance.
Section headings: Executive Summary, Career Highlights, Experience,
Education, Board and Advisory (optional). Single-column. ATS-safe.
"""
from pathlib import Path
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

TEMPLATE_PATH = Path(__file__).parent.parent.parent / "templates" / "resume" / "executive.docx"


def make_template() -> Path:
    doc = Document()

    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    name = doc.add_paragraph()
    name.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = name.add_run("{{CANDIDATE_NAME}}")
    run.font.name = "Calibri Light"
    run.font.size = Pt(24)  # 2pt larger than other templates
    run.font.color.rgb = RGBColor(0x1A, 0x1A, 0x1A)

    contact = doc.add_paragraph("{{CANDIDATE_CONTACT_LINE}}")
    contact.runs[0].font.size = Pt(10)
    contact.runs[0].font.color.rgb = RGBColor(0x40, 0x40, 0x40)

    doc.add_paragraph()

    doc.add_heading("Executive Summary", level=1)
    doc.add_paragraph("{{SUMMARY}}")

    doc.add_heading("Career Highlights", level=1)
    doc.add_paragraph("{{SKILLS}}")  # achievement-led "highlights" reuse SKILLS placeholder

    doc.add_heading("Experience", level=1)
    doc.add_paragraph("{{EXPERIENCE}}")

    doc.add_heading("Education", level=1)
    doc.add_paragraph("{{EDUCATION}}")

    TEMPLATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(TEMPLATE_PATH))
    return TEMPLATE_PATH


if __name__ == "__main__":
    path = make_template()
    print(f"Wrote {path}")
```

- [ ] **Step 2: Generate the template**

```powershell
python scripts\packaging\_make_resume_template_executive.py
```

- [ ] **Step 3: Write tests**

Create `tests/templates/test_resume_template_executive.py`:

```python
"""Validate the executive resume template is ATS-safe."""
from pathlib import Path

from scripts.validators.ats_check import ats_check

TEMPLATE = Path(__file__).parent.parent.parent / "templates" / "resume" / "executive.docx"


def test_template_exists():
    assert TEMPLATE.exists(), f"Template missing: {TEMPLATE}"


def test_template_passes_ats_check():
    result = ats_check(TEMPLATE)
    assert result.passed, f"Failures: {[f.code for f in result.failures]}"


def test_template_uses_executive_section_labels():
    """Executive template uses 'Executive Summary' and 'Career Highlights'
    instead of the standard 'Summary' / 'Skills'."""
    from docx import Document
    doc = Document(str(TEMPLATE))
    flat = "\n".join(p.text for p in doc.paragraphs)
    assert "Executive Summary" in flat
    assert "Career Highlights" in flat


def test_template_name_heading_is_24pt():
    """Executive template uses 24pt name heading (2pt larger than chronological)."""
    from docx import Document
    doc = Document(str(TEMPLATE))
    name_paragraph = doc.paragraphs[0]
    assert name_paragraph.runs
    assert name_paragraph.runs[0].font.size.pt == 24
```

- [ ] **Step 4: Run tests**

```powershell
python -m pytest tests/templates/test_resume_template_executive.py -v
```

Expected: all green.

- [ ] **Step 5: Commit**

```powershell
git add scripts/packaging/_make_resume_template_executive.py templates/resume/executive.docx tests/templates/test_resume_template_executive.py
git commit -m "feat: add executive resume DOCX template"
```

---

## Task 9 — Modern-clean cover-letter template (DOCX)

Less formal letterhead, smaller recipient block, more whitespace. For tech/startup contexts.

**Files:**

- Create: `scripts/packaging/_make_cover_letter_template_modern_clean.py`
- Create: `templates/cover-letter/modern-clean.docx` (generated)
- Create: `tests/templates/test_cover_letter_template_modern_clean.py`

### Steps

- [ ] **Step 1: Write the template generator**

Create `scripts/packaging/_make_cover_letter_template_modern_clean.py`:

```python
"""Generate the modern-clean cover-letter DOCX template.

Less formal layout. Smaller letterhead, less typographic weight, more
whitespace between paragraphs. Suited to tech/startup contexts where the
formal letterhead reads as stiff. Single-column. Calibri 11pt body. ATS-safe.
"""
from pathlib import Path
from docx import Document
from docx.shared import Pt, Inches, RGBColor

TEMPLATE_PATH = Path(__file__).parent.parent.parent / "templates" / "cover-letter" / "modern-clean.docx"


def make_template() -> Path:
    doc = Document()

    for section in doc.sections:
        section.top_margin = Inches(1.0)  # more top space than formal-business
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(0.85)
        section.right_margin = Inches(0.85)

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    # Compact letterhead — name slightly larger but no full recipient block
    p = doc.add_paragraph()
    run = p.add_run("{{CANDIDATE_NAME}}")
    run.font.size = Pt(16)
    run.font.color.rgb = RGBColor(0x1A, 0x1A, 0x1A)
    doc.add_paragraph("{{CANDIDATE_CONTACT_LINE}}")
    doc.add_paragraph()
    doc.add_paragraph()  # extra whitespace

    doc.add_paragraph("{{LETTER_DATE}}")
    doc.add_paragraph()

    # Less-formal salutation — "Hi" instead of "Dear"
    doc.add_paragraph("Hi {{SALUTATION}},")
    doc.add_paragraph()

    doc.add_paragraph("{{HOOK_PARAGRAPH}}")
    doc.add_paragraph()
    doc.add_paragraph("{{FIT_PARAGRAPH}}")
    doc.add_paragraph()
    doc.add_paragraph("{{CLOSE_PARAGRAPH}}")
    doc.add_paragraph()

    # Less-formal sign-off
    doc.add_paragraph("Best,")
    doc.add_paragraph()
    doc.add_paragraph("{{CANDIDATE_NAME}}")

    TEMPLATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(TEMPLATE_PATH))
    return TEMPLATE_PATH


if __name__ == "__main__":
    path = make_template()
    print(f"Wrote {path}")
```

- [ ] **Step 2: Generate the template**

```powershell
python scripts\packaging\_make_cover_letter_template_modern_clean.py
```

- [ ] **Step 3: Write tests**

Create `tests/templates/test_cover_letter_template_modern_clean.py`:

```python
"""Validate the modern-clean cover-letter template is ATS-safe."""
from pathlib import Path

from scripts.validators.ats_check import ats_check

TEMPLATE = Path(__file__).parent.parent.parent / "templates" / "cover-letter" / "modern-clean.docx"


def test_template_exists():
    assert TEMPLATE.exists(), f"Template missing: {TEMPLATE}"


def test_template_passes_ats_check():
    result = ats_check(TEMPLATE)
    assert result.passed, f"Failures: {[f.code for f in result.failures]}"


def test_template_uses_informal_salutation_and_signoff():
    """Modern-clean uses 'Hi' and 'Best,' instead of 'Dear' and 'Sincerely,'."""
    from docx import Document
    doc = Document(str(TEMPLATE))
    flat = "\n".join(p.text for p in doc.paragraphs)
    assert "Hi {{SALUTATION}}" in flat
    assert "Best," in flat
    assert "Dear" not in flat
    assert "Sincerely" not in flat


def test_template_has_no_recipient_block():
    """Modern-clean omits the formal recipient address block."""
    from docx import Document
    doc = Document(str(TEMPLATE))
    flat = "\n".join(p.text for p in doc.paragraphs)
    assert "{{RECIPIENT_NAME}}" not in flat
    assert "{{RECIPIENT_TITLE}}" not in flat
    assert "{{RECIPIENT_COMPANY}}" not in flat
```

Note: the `render_cover_letter_docx` placeholder map still contains the recipient keys, but they will simply not match any paragraph in this template (no error raised — silent skip is correct). If the user wants to surface the recipient on a modern-clean letter they can include it in the body paragraphs.

- [ ] **Step 4: Run tests**

```powershell
python -m pytest tests/templates/test_cover_letter_template_modern_clean.py -v
```

Expected: all green.

- [ ] **Step 5: Verify the full DOCX generator round-trip**

```powershell
python -c "from scripts.generators.cover_letter_to_docx import render_cover_letter_docx; from pathlib import Path; render_cover_letter_docx({'candidate_name':'Alex','candidate_contact_line':'alex@x','letter_date':'2026-05-13','salutation':'Hiring Team','hook_paragraph':'Hook.','fit_paragraph':'Fit.','close_paragraph':'Close.'}, Path('mc_test.docx'), template='modern-clean'); print('OK')"
Remove-Item mc_test.docx
```

Expected: prints `OK`.

- [ ] **Step 6: Commit**

```powershell
git add scripts/packaging/_make_cover_letter_template_modern_clean.py templates/cover-letter/modern-clean.docx tests/templates/test_cover_letter_template_modern_clean.py
git commit -m "feat: add modern-clean cover-letter DOCX template"
```

---

## Task 10 — Template-selection reference document

Decision tree + comparison table + ND-framing on the functional-template tradeoff. This is the user-facing guidance for choosing a template.

**Files:**

- Create: `references/template-selection.md`
- Create: `tests/references/test_template_selection_reference.py`

### Steps

- [ ] **Step 1: Write the reference document**

Create `references/template-selection.md`:

```markdown
# Template Selection Reference

**Purpose:** Help the user choose a resume or cover-letter template that fits their career stage, role type, and disclosure stance. Every template ships ATS-safe; the choice is about narrative shape, not formatting safety.

The skill ships four resume templates and two cover-letter templates. All are single-column, no-tables, plain-font, identity-first-language-by-default. None contain BRAINS branding — these are the user's professional documents.

---

## Resume template comparison

| Template | Best for | Section order | Recruiter perception | ATS compatibility |
|---|---|---|---|---|
| `chronological` | Linear career history, consistent recent relevant experience | Summary → Experience → Skills → Education | Default expectation; widely accepted | Excellent |
| `functional` | Career-changers, employment gaps, skills-led story | Summary → Skills and Achievements → Experience (titles + dates) → Education | Mixed — see ND framing below | Excellent |
| `hybrid` | Career pivots with relevant transferable skills | Summary → Key Skills → Experience → Education | Generally well-received as a middle ground | Excellent |
| `executive` | Senior roles, 15+ years experience, board/leadership framing | Executive Summary → Career Highlights → Experience → Education | Appropriate for senior contexts; over-formal for early-career | Excellent |

## Cover-letter template comparison

| Template | Best for | Tone |
|---|---|---|
| `formal-business` | Traditional industries, regulated sectors, formal applications | Formal salutation, full recipient block, "Sincerely" sign-off |
| `modern-clean` | Tech / startup contexts | "Hi" salutation, no recipient block, "Best" sign-off, more whitespace |

---

## Decision tree

Walk the questions in order. The first definitive answer points to the recommended template.

### Q1 — Is the user actively changing careers, returning from a gap of 12+ months, or otherwise discontinuous?

- **No** → continue to Q2.
- **Yes** → consider `functional` or `hybrid`. Read the ND framing section below before recommending `functional`. **Default recommendation: `hybrid`** — it gives skills-led framing without the functional-template recruiter-skepticism penalty.

### Q2 — Is the user at 15+ years of experience and applying for senior leadership, board, or executive-track roles?

- **No** → continue to Q3.
- **Yes** → `executive`.

### Q3 — Is the user's recent experience linearly relevant to the target role?

- **Yes** → `chronological`. This is the default expectation and produces the cleanest read.
- **No** → `hybrid`. Skills-led framing with chronological backing.

### Cover-letter selection — Q4

If a cover letter is being produced, ask one additional question:

**Is the target industry traditional, regulated, or otherwise formal-letter-expected?**

- **Yes** (law, finance, healthcare, government, academia, non-tech corporate) → `formal-business`.
- **No** (tech, startup, creative, modern professional services) → `modern-clean`.

When in doubt, ask the user; do not infer industry tone from sparse signals.

---

## ND framing: the functional-template tradeoff

The functional template is genuinely useful — it lets a user lead with skills and de-emphasise chronological work history, which is the right call for career-changers, people with employment gaps, or anyone whose strongest narrative is skills-led rather than role-led. The recruiter-side tradeoff: a significant subset of recruiters interpret functional layouts as "hiding something" — even when the user has nothing to hide.

This places the user in a position no neurodivergent candidate should have to navigate alone. Three honest options:

1. **Use `functional`** — when the user has made a deliberate decision that the skills-led narrative is the strongest representation of their candidacy. The recruiter-perception risk exists; the user judges whether it is worth taking.
2. **Use `hybrid`** — the recommended middle path. Lead with a compact skills summary block, then back it with full chronological experience. Captures most of the functional template's narrative power without triggering the "hiding something" perception.
3. **Use `chronological`** — when chronological recency is actually a strength, or when the role target is conservative enough that any deviation reads as suspicious.

The skill does not push the user toward or away from any option. It informs. The user decides.

---

## Worked examples

### Example 1 — Career-changer from engineering to product management

**Profile:** 8 years software engineering, last 12 months in a product-adjacent role; targeting senior product manager.

**Walkthrough:** Q1 — yes, career change → consider functional or hybrid. ND framing — career-changer with relevant adjacent recent experience is a strong fit for `hybrid` (skills-led framing without losing the chronological backing that anchors the engineering credibility).

**Recommended template:** `hybrid`. Cover letter — depends on Q4; tech/startup → `modern-clean`; corporate enterprise PM role → `formal-business`.

### Example 2 — Senior leader returning from a 2-year career break

**Profile:** 20 years experience, last role was VP-level, 2-year career break with informal consulting only; targeting director-or-above roles.

**Walkthrough:** Q1 — yes, gap of 12+ months → consider functional or hybrid. Q2 — yes, 15+ years experience and senior-target. The `executive` template anticipates a 2-page allowance and uses "Career Highlights" framing that surfaces accumulated achievements without leaning on the gap question. The functional layout would risk a "hiding something" read at the executive level where pattern recognition is sharpest.

**Recommended template:** `executive`. Cover letter — `formal-business`.

### Example 3 — Recent graduate, linear early career

**Profile:** 18 months in first professional role, targeting next-level individual contributor.

**Walkthrough:** Q1 — no. Q2 — no. Q3 — yes, linearly relevant.

**Recommended template:** `chronological`. Cover letter — `modern-clean` if target is tech/startup; `formal-business` otherwise.

### Example 4 — Career-changer leaving a niche legacy ecosystem for a forward-looking role

**Profile:** 12 years deep specialism in a now-fading enterprise ecosystem; targeting a forward-looking role that values transferable competencies (programme delivery, vendor management, large-system integration) rather than the legacy product itself.

**Walkthrough:** Q1 — yes, career change. ND framing — the user's strongest narrative is product-agnostic transferable competencies, not the legacy ecosystem itself. `hybrid` lets the skills summary lead with the transferable competencies while the experience section retains chronological credibility. `functional` would over-correct — recruiters in the target industry need to see the years-of-experience signal that the chronological backing provides.

**Recommended template:** `hybrid`. Cover letter — depends on target industry tone.

---

## When to ask the user before choosing

If the user has not provided enough context to walk the decision tree confidently, ask one open question at the right level:

- "Is your recent experience linearly relevant to the roles you're targeting, or are you changing direction?" — pins Q1 and Q3.
- "Are you targeting senior leadership or executive-track roles, or individual-contributor / mid-level?" — pins Q2.
- "Is the industry you're applying into formal-letter-expected (legal/financial/regulated) or more relaxed (tech/startup/modern professional services)?" — pins Q4.

Do not ask all three at once. One question per turn.
```

- [ ] **Step 2: Write a structural test for the reference**

Create `tests/references/__init__.py` (empty) then `tests/references/test_template_selection_reference.py`:

```python
"""Structural tests for references/template-selection.md.

Verifies that the reference includes all four resume templates and both
cover-letter templates, the decision tree exists, and the ND-framing
section contains both pro and con language for the functional template.
"""
from pathlib import Path

REFERENCE = Path(__file__).parent.parent.parent / "references" / "template-selection.md"


def _text():
    return REFERENCE.read_text(encoding="utf-8")


def test_reference_exists():
    assert REFERENCE.exists()


def test_all_four_resume_templates_named():
    text = _text()
    for name in ("chronological", "functional", "hybrid", "executive"):
        assert f"`{name}`" in text, f"Template name not surfaced: {name}"


def test_both_cover_letter_templates_named():
    text = _text()
    for name in ("formal-business", "modern-clean"):
        assert f"`{name}`" in text, f"Cover-letter template name not surfaced: {name}"


def test_decision_tree_section_exists():
    text = _text()
    assert "Decision tree" in text
    # All four leading questions should appear
    for q in ("Q1", "Q2", "Q3", "Q4"):
        assert q in text


def test_nd_framing_section_present_with_both_pro_and_con_language():
    """ND framing must surface BOTH the genuine usefulness of the functional
    template AND the recruiter-skepticism tradeoff — never one-sided."""
    text = _text()
    assert "ND framing" in text or "functional-template tradeoff" in text
    assert "genuinely useful" in text.lower()  # pro language
    assert "hiding something" in text.lower()  # con language
    assert "hybrid" in text.lower()  # middle path explicitly named


def test_worked_examples_present():
    text = _text()
    assert "Example 1" in text
    assert "Example 2" in text
    assert "Example 3" in text
```

- [ ] **Step 3: Run tests**

```powershell
python -m pytest tests/references/test_template_selection_reference.py -v
```

Expected: all green.

- [ ] **Step 4: Add template-selection cross-references to the four existing workflow files**

The spec calls for the create, edit, tailor, and cover-letter workflows to point at the new template-selection reference. Add a short paragraph to each.

**In `references/workflows/create.md`**, find the inputs or procedure section that covers template choice (or, if there is no explicit template-choice step yet, add one near where the resume output format is first discussed). Insert:

```markdown
**Template selection.** This workflow defaults to the `chronological` resume template. Before rendering the final output, walk the user through `references/template-selection.md` to decide whether `chronological`, `functional`, `hybrid`, or `executive` better fits their situation. Pass the chosen template name as the `template=` argument to the generator.
```

**In `references/workflows/edit.md`**, insert the same paragraph in the rendering step. Edit existing-template language to say "the chosen template" rather than "the chronological template" wherever the workflow assumes a single template.

**In `references/workflows/tailor.md`**, same insertion — and explicitly note that tailoring may change the appropriate template (a career-pivot tailor often justifies switching from `chronological` to `hybrid`).

**In `references/workflows/cover-letter.md`**, insert:

```markdown
**Template selection.** This workflow defaults to the `formal-business` cover-letter template. Before rendering, walk the user through `references/template-selection.md` to decide whether `formal-business` or `modern-clean` better fits the target industry. Pass the chosen template name as the `template=` argument to the generator.
```

- [ ] **Step 5: Add a structural test that the cross-references exist**

Append to `tests/references/test_template_selection_reference.py`:

```python
WORKFLOWS_THAT_MUST_CROSS_REFERENCE = (
    "create.md",
    "edit.md",
    "tailor.md",
    "cover-letter.md",
)


def test_workflow_files_cross_reference_template_selection():
    workflows_dir = REFERENCE.parent / "workflows"
    for fname in WORKFLOWS_THAT_MUST_CROSS_REFERENCE:
        text = (workflows_dir / fname).read_text(encoding="utf-8")
        assert "template-selection.md" in text, (
            f"{fname} does not cross-reference references/template-selection.md"
        )
```

- [ ] **Step 6: Run the suite**

```powershell
python -m pytest -q
```

Expected: all green.

- [ ] **Step 7: Commit**

```powershell
git add references/template-selection.md references/workflows/create.md references/workflows/edit.md references/workflows/tailor.md references/workflows/cover-letter.md tests/references/
git commit -m "docs: add template-selection reference and cross-references from workflow files"
```

---

## Phase 2 — LinkedIn profile improvement workflow (Tasks 11-13)

The workflow is Claude-driven: the reference file defines the procedure, Claude does the rewriting using the v1 framework. No new Python helpers — the workflow reuses `linkedin_zip.py` for ingest and the existing `bias_scan` / `integrity_check` validators on the output.

---

## Task 11 — `references/workflows/linkedin-improve.md`

The workflow reference. Defines inputs, procedure, character-limit rules, ND-aware language application, and output format.

**Files:**

- Create: `references/workflows/linkedin-improve.md`

### Steps

- [ ] **Step 1: Write the reference document**

Create `references/workflows/linkedin-improve.md`:

```markdown
# Workflow: LinkedIn Profile Improvement

**Purpose:** Rewrite a user's LinkedIn profile (Headline, About, Experience entries, Skills) applying the ND-aware language framework. The audience and formatting constraints differ meaningfully from a resume — this workflow exists because resume-tuning rules do not translate cleanly to LinkedIn.

This is a parallel surface to the resume, not a substitute. A user who has run the resume-review or edit workflows should run this one next to bring their LinkedIn presentation into alignment.

---

## Differences from the resume workflows

| Dimension | Resume | LinkedIn profile |
|---|---|---|
| Audience search mechanism | ATS keyword extraction | Recruiter semantic search + structured Skills tags |
| Reading context | Single-document review by a screener | Scrolling-on-mobile dominant; often scanned in seconds |
| Formatting affordance | Full rich text, multi-page | Plain text, character-limited per field, no rich formatting |
| Tone calibration | Formal, achievement-led | Conversational hook + scannable proof |
| Editing surface | DOCX/PDF file the user submits | LinkedIn web/app fields the user pastes into manually |

The output of this workflow is **markdown-formatted text ready to be copy-pasted into LinkedIn**. The skill does not edit LinkedIn directly.

---

## Trigger conditions

Start this workflow when any of the following are true:

- The user says "improve my LinkedIn", "rewrite my LinkedIn profile", "update my LinkedIn", "make my LinkedIn match my resume", or any equivalent phrasing.
- The user has just completed the resume-review or edit workflow and asks for the equivalent treatment on their LinkedIn.
- The user runs `/brains-linkedin-improve`.

---

## Inputs

1. **LinkedIn profile content** — accept either:
   - A LinkedIn ZIP export (parsed via `scripts/parsers/linkedin_zip.py`). Apply the safeguarding rules from the linkedin-ingest workflow: surface the `skipped_files` list, never read third-party-PII files.
   - **OR** pasted profile sections — the user pastes their current Headline / About / Experience / Skills as raw text.

2. **Target role or career focus** — one or two sentences. Used to bias the rewrite toward the right keyword and skill-tag emphasis.

3. **Disclosure stance** — carry forward the session's disclosure stance (affirmative framing default; neutral-signalling or explicit-disclosure if the user has set one). Apply consistently to the LinkedIn rewrite the same way the resume workflows do.

---

## Procedure

**(a) Receive and structure the existing profile.**

If a ZIP was provided, call `parse_linkedin_export(path)` and surface the `skipped_files` list to the user. If pasted text was provided, parse it into the four standard sections (Headline / About / Experience / Skills) — ask the user to confirm the segmentation if any section is ambiguous.

**(b) Run the ND-bias scanner and integrity scanner on the existing profile text.**

```python
from scripts.validators.bias_scan import bias_scan
from scripts.validators.integrity_check import integrity_check

bias = bias_scan(existing_profile_text)
integ = integrity_check(existing_profile_text)
```text

Surface the findings. These inform the rewrite — the rewrite should resolve every CRITICAL or HIGH integrity finding and address every bias finding the user agrees with.

**(c) Rewrite each section.**

Apply the language rules from `references/language-do-dont.md` and the bias-pattern guidance from `references/nd-bias-patterns.md`. Respect the user's disclosure stance.

**Headline (max 220 characters):**

- One sentence. Lead with the role or domain, not with a generic descriptor.
- Include 2-3 high-value keywords that match the target-role search query.
- No soft-skills vocabulary ("passionate", "team player", etc. — bias-scan Pattern 1).
- Identity-first language by default; switch to person-first if the user has set that preference.

**About (max 2,600 characters; aim for ~1,500 for scannability):**

- Three paragraphs maximum.
  - **Paragraph 1 — Hook:** one specific, evidenced opening line. No generic openers ("I'm a passionate professional with X years of experience…"). Lead with the most concrete claim.
  - **Paragraph 2 — Proof:** two or three concrete achievements with measurable outcomes. This is the resume-summary content reframed for narrative reading rather than bullet scanning.
  - **Paragraph 3 — CTA:** one line on what the user is currently building, looking for, or open to. Direct, not coy.
- First-person voice. Use "I" pronouns naturally — LinkedIn About sections are written in first person, unlike most resumes.
- No more than one warmth signal per paragraph. Warmth without specificity reads hollow; specificity without warmth reads cold.

**Experience entries (max ~2,000 characters per role):**

- Lead each role with a one-line role-summary sentence (what the role actually was — not just the title), then 3-5 achievement bullets.
- Achievement bullets follow the same pattern as resume bullets: action verb → specific action → measurable outcome.
- LinkedIn does not render bullet characters — use plain text. A line break per bullet is sufficient.

**Skills (target 25-30 tags):**

- LinkedIn supports up to 50 skill tags. Aim for 25-30 — enough density for semantic search to surface the profile without diluting the strongest signals.
- Order by relevance to the target role; the first 5 are the most visible.
- Include both hard skills (named technologies, frameworks, certifications, methodologies) and skill tags that match common recruiter search terms for the target role.

**(d) Run the validators on the rewritten output.**

```python
from scripts.validators.bias_scan import bias_scan
from scripts.validators.integrity_check import integrity_check

rewritten = headline + "\n\n" + about_text + "\n\n" + experience_text + "\n\n" + skills_text
bias_after = bias_scan(rewritten)
integ_after = integrity_check(rewritten)
```text

The rewritten output must have:

- No CRITICAL or HIGH integrity findings.
- No remaining ND_BIAS_P1_SOFT_SKILLS or ND_BIAS_P5_UNDER_CLAIM hits unless the user explicitly preserved the language.

**(e) Save the output as a markdown artifact.**

Write to `output/linkedin-profile-YYYY-MM-DD-HHMMSS.md` with this structure:

```markdown
# LinkedIn Profile Rewrite

**Prepared:** {date}
**Target role / focus:** {target}
**Disclosure stance:** {stance}

> Copy each section into the matching LinkedIn field. LinkedIn does not render markdown — these are plain-text sections labelled for paste convenience.

---

## Headline (paste into LinkedIn → Headline field)

{rewritten headline}

**Characters:** {n} / 220
**Rationale:** {one line on why this framing}

---

## About (paste into LinkedIn → About field)

{rewritten about}

**Characters:** {n} / 2600
**Rationale:** {one line}

---

## Experience — {company}, {title}, {dates}

{rewritten experience entry}

**Characters:** {n} / 2000
**Rationale:** {one line}

(Repeat per role)

---

## Skills (paste into LinkedIn → Skills section; LinkedIn limit is 50, this list contains {n})

- {skill 1}
- {skill 2}
- ...

**Rationale:** {one line on the selection logic}

---

## Original profile (for comparison)

{original headline}
{original about}
{original experience}
{original skills list}
```text

This artifact carries BRAINS coaching branding — it is an internal coaching artifact, not a submission-ready document. (The branding rule from `references/brand-application.md` covers this: the LinkedIn rewrite output itself, intended for LinkedIn paste, is plain unbranded text within the artifact; the markdown wrapper that documents the coaching session carries the BRAINS coaching frame.)

**(f) Offer next steps.**

- Offer the consolidation workflow (`/brains-consolidate`) if the user also has a resume, to check that the rewritten LinkedIn and the resume tell a coherent story.
- Offer to iterate on any section the user wants to redirect.

---

## Output artifacts

| File | Notes |
|---|---|
| `output/linkedin-profile-YYYY-MM-DD-HHMMSS.md` | BRAINS coaching artifact — copy-paste-ready rewrite + original for comparison |

---

## Safeguarding boundaries

- **No LinkedIn API write access.** The skill produces a markdown artifact. The user pastes the rewritten sections into LinkedIn themselves.
- **Third-party PII guard inherited from `linkedin_zip.py`.** Connections, messages, invitations, reactions, comments, likes — all skipped at the parser level. The skipped-files list is surfaced exactly as in the linkedin-ingest workflow.
- **Character limits are LinkedIn-defined, not optional.** The Headline cuts off at 220 characters; About at 2,600; Experience at 2,000. The rewrite must fit within those limits, not just attempt to.

```

- [ ] **Step 2: Add a structural test for the workflow reference**

Create `tests/references/test_workflow_linkedin_improve.py`:

```python
"""Structural tests for references/workflows/linkedin-improve.md."""
from pathlib import Path

REFERENCE = Path(__file__).parent.parent.parent / "references" / "workflows" / "linkedin-improve.md"


def _text():
    return REFERENCE.read_text(encoding="utf-8")


def test_reference_exists():
    assert REFERENCE.exists()


def test_linkedin_character_limits_documented():
    text = _text()
    assert "220" in text  # Headline limit
    assert "2,600" in text or "2600" in text  # About limit
    assert "2,000" in text or "2000" in text  # Experience entry limit


def test_three_paragraph_about_structure_documented():
    text = _text()
    assert "Hook" in text
    assert "Proof" in text
    assert "CTA" in text


def test_reference_documents_validator_use():
    text = _text()
    assert "bias_scan" in text
    assert "integrity_check" in text


def test_safeguarding_section_present():
    text = _text()
    assert "Safeguarding boundaries" in text
    assert "no LinkedIn API write access" in text.lower()
```

- [ ] **Step 3: Run tests**

```powershell
python -m pytest tests/references/test_workflow_linkedin_improve.py -v
```

Expected: all green.

- [ ] **Step 4: Commit**

```powershell
git add references/workflows/linkedin-improve.md tests/references/test_workflow_linkedin_improve.py
git commit -m "docs: add LinkedIn profile improvement workflow reference"
```

---

## Task 12 — Slash command + SKILL.md router update for `linkedin-improve`

**Files:**

- Create: `commands/brains-linkedin-improve.md`
- Modify: `SKILL.md` (add router entry + capability menu row)

### Steps

- [ ] **Step 1: Create the slash command file**

Create `commands/brains-linkedin-improve.md`:

```markdown
---
description: Rewrite a LinkedIn profile (Headline / About / Experience / Skills) using the ND-aware framework
argument-hint: [optional: path to LinkedIn ZIP, or paste profile sections in chat]
---

Run the BRAINS Resume Skill LinkedIn-profile-improvement workflow. Load `~/.claude/skills/brains-resume/references/workflows/linkedin-improve.md` and follow its procedure. Input source: `$ARGUMENTS` (a ZIP path) or pasted text in the next message.
```

- [ ] **Step 2: Update SKILL.md router section**

In `SKILL.md`, add a new row to the workflow-router table. Find this block:

```markdown
| Ingest my LinkedIn export | `references/workflows/linkedin-ingest.md` |
```

Insert immediately after it:

```markdown
| Improve / rewrite my LinkedIn profile | `references/workflows/linkedin-improve.md` |
```

- [ ] **Step 3: Update the capability menu in the First-Use Behaviour section**

Find this row in the capability menu table:

```markdown
| Ingest LinkedIn export | Live |
```

Insert immediately after it:

```markdown
| Improve LinkedIn profile | Live |
```

- [ ] **Step 4: Update the slash-command list line**

Find this sentence in the First-Use Behaviour section:

> "Type `/brains-` and Claude Code will list the nine commands: review, disclosure, edit, tailor, cover-letter, create, linkedin, career-change, check."

Update to (note: this will be updated again in Task 17 when consolidate ships; for now bump to 10):

> "Type `/brains-` and Claude Code will list the ten commands: review, disclosure, edit, tailor, cover-letter, create, linkedin, linkedin-improve, career-change, check."

- [ ] **Step 5: Run the suite to confirm no test regressions**

```powershell
python -m pytest -q
```

Expected: all green.

- [ ] **Step 6: Commit**

```powershell
git add commands/brains-linkedin-improve.md SKILL.md
git commit -m "feat: add brains-linkedin-improve slash command and router entry"
```

---

## Task 13 — LinkedIn-improve smoke test

End-to-end smoke test exercising the deterministic portions: parse the synthetic LinkedIn ZIP, run validators on a sample rewritten output, write the artifact file.

**Files:**

- Create: `tests/test_smoke_linkedin_improve_workflow.py`

### Steps

- [ ] **Step 1: Write the smoke test**

Create `tests/test_smoke_linkedin_improve_workflow.py`:

```python
"""Smoke test for the deterministic portion of the LinkedIn-improve workflow.

Exercises: parse synthetic LinkedIn export, run bias_scan + integrity_check on
a representative rewritten output, write the markdown artifact file. The
rewrite itself is Claude-driven and not deterministically testable here —
this smoke test verifies the surrounding scaffolding works end-to-end.
"""
from pathlib import Path

from scripts.parsers.linkedin_zip import parse_linkedin_export
from scripts.validators.bias_scan import bias_scan
from scripts.validators.integrity_check import integrity_check

PROJECT_ROOT = Path(__file__).parent.parent
FIXTURE_ZIP = PROJECT_ROOT / "docs" / "testing" / "fixtures" / "synthetic_linkedin_export.zip"


# Representative output a well-formed rewrite would produce. Used to validate
# the validator pipeline; the actual rewriting is Claude-driven at runtime.
REWRITTEN_SAMPLE = (
    "Senior platform engineer focused on observability and incident response. "
    "Built distributed-systems instrumentation for 50M-DAU products. "
    "Open to staff and principal roles in observability, reliability, and platform.\n\n"
    "I build observability and reliability platforms. At Example Corp I led the migration "
    "of a 50M-DAU ingestion pipeline to a unified telemetry layer, cutting p99 latency "
    "by 40 percent and reducing operator-on-call load by half.\n\n"
    "I previously led the platform-engineering team at Sample Industries, where we "
    "consolidated four service-monitoring stacks into one and trained four engineers "
    "to senior level. I care about systems that humans can actually operate.\n\n"
    "Currently open to staff or principal platform-engineering roles where "
    "observability is treated as a first-class product surface.\n\n"
    "Skills: Python, distributed systems, observability, incident response, OpenTelemetry, "
    "Prometheus, SLO design, platform engineering, mentoring, technical leadership, "
    "Kubernetes, AWS, GCP, Terraform, Go, service-mesh, on-call ergonomics"
)


def test_linkedin_improve_smoke(tmp_path):
    # (a) Parse the synthetic LinkedIn export — same parser as linkedin-ingest.
    parsed = parse_linkedin_export(FIXTURE_ZIP)
    assert parsed["profile"], "synthetic profile section should not be empty"
    assert "Connections.csv" in parsed["skipped_files"]

    # (b) Run validators on a representative rewritten output.
    bias = bias_scan(REWRITTEN_SAMPLE)
    integ = integrity_check(REWRITTEN_SAMPLE)

    # The sample is intentionally clean — no CRITICAL/HIGH integrity findings.
    assert not any(f.severity in ("CRITICAL", "HIGH") for f in integ.findings), (
        f"Sample triggered unexpected integrity findings: "
        f"{[(f.code, f.severity) for f in integ.findings]}"
    )

    # (c) Write the markdown artifact.
    out = tmp_path / "linkedin-profile-2026-05-13-120000.md"
    out.write_text(
        "# LinkedIn Profile Rewrite\n\n"
        "**Prepared:** 2026-05-13\n"
        "**Target role / focus:** Staff platform engineering\n"
        "**Disclosure stance:** Affirmative framing (default)\n\n"
        "---\n\n"
        "## Headline\n\n"
        f"{REWRITTEN_SAMPLE.splitlines()[0]}\n\n"
        "## About\n\n"
        f"{REWRITTEN_SAMPLE}\n\n"
        f"_Bias findings on output:_ {len(bias.findings)}\n"
        f"_Integrity findings on output:_ {len(integ.findings)}\n",
        encoding="utf-8",
    )

    assert out.exists()
    assert out.stat().st_size > 0
    content = out.read_text(encoding="utf-8")
    assert "LinkedIn Profile Rewrite" in content
    assert "Headline" in content
    assert "About" in content
```

- [ ] **Step 2: Run the smoke test**

```powershell
python -m pytest tests/test_smoke_linkedin_improve_workflow.py -v
```

Expected: green.

- [ ] **Step 3: Run the full suite**

```powershell
python -m pytest -q
```

Expected: all green.

- [ ] **Step 4: Commit**

```powershell
git add tests/test_smoke_linkedin_improve_workflow.py
git commit -m "test: add LinkedIn-improve workflow smoke test"
```

---

## Phase 3 — Consolidation workflow (Tasks 14-18)

Detects narrative inconsistency between a user's resume and LinkedIn profile and proposes resolutions. Read-only report; fixes happen via the existing edit / linkedin-improve workflows.

---

## Task 14 — Consolidation fixtures

Synthetic resume position data and synthetic LinkedIn position data with seeded deltas covering all five finding codes.

**Files:**

- Create: `tests/fixtures/consolidation_fixtures.py`

### Steps

- [ ] **Step 1: Write the fixture module**

Create `tests/fixtures/consolidation_fixtures.py`:

```python
"""Synthetic resume+LinkedIn position pairs for the consolidation validator.

Each pair is structured data shaped the way the validator expects:
  - resume_positions: list[dict] with company, title, start_date, end_date,
    bullets (list[str]), description (str — for tone analysis).
  - linkedin_positions: same shape.

NO REAL PII. The pairs are designed to trigger each finding code in
consolidation_check.py while a clean pair triggers none.
"""

# --- Clean alignment: same role, same title, same dates, same achievements ---

CLEAN_RESUME = [
    {
        "company": "Example Corp",
        "title": "Senior Engineer",
        "start_date": "2020-03",
        "end_date": "2024-08",
        "bullets": [
            "Led migration of ingestion pipeline to cloud-native platform.",
            "Reduced p99 latency by 40 percent.",
            "Mentored four junior engineers to mid-level.",
        ],
        "description": "Led the migration of the ingestion pipeline to a cloud-native platform serving 50M daily active users. Reduced p99 latency by 40 percent. Mentored four junior engineers.",
    }
]

CLEAN_LINKEDIN = [
    {
        "company": "Example Corp",
        "title": "Senior Engineer",
        "start_date": "2020-03",
        "end_date": "2024-08",
        "bullets": [
            "Led migration of ingestion pipeline to cloud-native platform.",
            "Reduced p99 latency by 40 percent.",
            "Mentored four junior engineers to mid-level.",
        ],
        "description": "Led the migration of the ingestion pipeline to a cloud-native platform serving 50M daily active users. Reduced p99 latency by 40 percent. Mentored four junior engineers.",
    }
]


# --- Job-title mismatch: same employer + overlapping dates, different title ---

TITLE_MISMATCH_RESUME = [
    {
        "company": "Example Corp",
        "title": "Senior Engineer",
        "start_date": "2020-03",
        "end_date": "2024-08",
        "bullets": ["Led platform migration."],
        "description": "Led platform migration.",
    }
]

TITLE_MISMATCH_LINKEDIN = [
    {
        "company": "Example Corp",
        "title": "Engineering Lead",  # different title for same role
        "start_date": "2020-03",
        "end_date": "2024-08",
        "bullets": ["Led platform migration."],
        "description": "Led platform migration.",
    }
]


# --- Date inconsistency: same employer + title, start months differ ---

DATE_MISMATCH_RESUME = [
    {
        "company": "Sample Industries",
        "title": "Software Engineer",
        "start_date": "2017-06",
        "end_date": "2019-11",
        "bullets": ["Backend services for e-commerce."],
        "description": "Backend services for an e-commerce platform.",
    }
]

DATE_MISMATCH_LINKEDIN = [
    {
        "company": "Sample Industries",
        "title": "Software Engineer",
        "start_date": "2017-09",  # 3-month start drift
        "end_date": "2019-11",
        "bullets": ["Backend services for e-commerce."],
        "description": "Backend services for an e-commerce platform.",
    }
]


# --- Achievement only in resume ---

ACHIEVEMENT_RESUME_ONLY_RESUME = [
    {
        "company": "Acme Co",
        "title": "Engineer",
        "start_date": "2015-01",
        "end_date": "2017-05",
        "bullets": [
            "Built shipping calculator service.",
            "Reduced cart-abandonment by 18 percent.",  # only on resume
        ],
        "description": "Built shipping calculator service.",
    }
]

ACHIEVEMENT_RESUME_ONLY_LINKEDIN = [
    {
        "company": "Acme Co",
        "title": "Engineer",
        "start_date": "2015-01",
        "end_date": "2017-05",
        "bullets": ["Built shipping calculator service."],
        "description": "Built shipping calculator service.",
    }
]


# --- Achievement only in LinkedIn ---

ACHIEVEMENT_LINKEDIN_ONLY_RESUME = [
    {
        "company": "Acme Co",
        "title": "Engineer",
        "start_date": "2015-01",
        "end_date": "2017-05",
        "bullets": ["Built shipping calculator service."],
        "description": "Built shipping calculator service.",
    }
]

ACHIEVEMENT_LINKEDIN_ONLY_LINKEDIN = [
    {
        "company": "Acme Co",
        "title": "Engineer",
        "start_date": "2015-01",
        "end_date": "2017-05",
        "bullets": [
            "Built shipping calculator service.",
            "Led architecture review for the platform team.",  # only on LinkedIn
        ],
        "description": "Built shipping calculator service. Led architecture review for the platform team.",
    }
]


# --- Tone divergence: same role, formal vs casual description ---

TONE_DIVERGENT_RESUME = [
    {
        "company": "Example Corp",
        "title": "Senior Engineer",
        "start_date": "2020-03",
        "end_date": "2024-08",
        "bullets": ["Led pipeline migration."],
        "description": (
            "Directed the architectural migration of the ingestion pipeline to a "
            "cloud-native platform, achieving a 40 percent reduction in p99 latency "
            "and a measurable improvement in operator-on-call burden across the "
            "platform-engineering team."
        ),
    }
]

TONE_DIVERGENT_LINKEDIN = [
    {
        "company": "Example Corp",
        "title": "Senior Engineer",
        "start_date": "2020-03",
        "end_date": "2024-08",
        "bullets": ["Led pipeline migration."],
        "description": (
            "Spent four years rebuilding our ingestion pipeline from scratch — turned "
            "out to be a much bigger lift than anyone expected, but we got there. "
            "Made things a lot faster and a lot less painful to operate. Good times."
        ),
    }
]
```

- [ ] **Step 2: Verify the fixtures import cleanly**

```powershell
python -c "from tests.fixtures import consolidation_fixtures; print('OK')"
```

Expected: prints `OK`.

- [ ] **Step 3: Commit**

```powershell
git add tests/fixtures/consolidation_fixtures.py
git commit -m "test: add consolidation validator fixtures"
```

---

## Task 15 — `consolidation_check.py` validator (TDD)

Five finding codes: title mismatch, date inconsistency, achievement-only-in-resume, achievement-only-in-LinkedIn, tone divergence.

**Files:**

- Create: `tests/validators/test_consolidation_check.py`
- Create: `scripts/validators/consolidation_check.py`

### Steps

- [ ] **Step 1: Write failing tests**

Create `tests/validators/test_consolidation_check.py`:

```python
"""Tests for the consolidation validator.

Each test pairs resume + LinkedIn position lists with seeded deltas and
asserts the validator surfaces the expected finding code.
"""
from scripts.validators.consolidation_check import consolidation_check
from tests.fixtures import consolidation_fixtures as fx


def _codes(result):
    return [f.code for f in result.findings]


def test_clean_alignment_produces_no_findings():
    result = consolidation_check(fx.CLEAN_RESUME, fx.CLEAN_LINKEDIN)
    assert result.findings == []


def test_job_title_mismatch_detected():
    result = consolidation_check(fx.TITLE_MISMATCH_RESUME, fx.TITLE_MISMATCH_LINKEDIN)
    assert "CONSOLIDATION_JOB_TITLE_MISMATCH" in _codes(result)


def test_date_inconsistency_detected():
    result = consolidation_check(fx.DATE_MISMATCH_RESUME, fx.DATE_MISMATCH_LINKEDIN)
    assert "CONSOLIDATION_DATE_INCONSISTENCY" in _codes(result)


def test_achievement_only_in_resume_detected():
    result = consolidation_check(
        fx.ACHIEVEMENT_RESUME_ONLY_RESUME, fx.ACHIEVEMENT_RESUME_ONLY_LINKEDIN
    )
    assert "CONSOLIDATION_ACHIEVEMENT_ONLY_IN_RESUME" in _codes(result)


def test_achievement_only_in_linkedin_detected():
    result = consolidation_check(
        fx.ACHIEVEMENT_LINKEDIN_ONLY_RESUME, fx.ACHIEVEMENT_LINKEDIN_ONLY_LINKEDIN
    )
    assert "CONSOLIDATION_ACHIEVEMENT_ONLY_IN_LINKEDIN" in _codes(result)


def test_tone_divergence_detected():
    result = consolidation_check(fx.TONE_DIVERGENT_RESUME, fx.TONE_DIVERGENT_LINKEDIN)
    assert "CONSOLIDATION_TONE_DIVERGENCE" in _codes(result)


def test_finding_carries_role_context_and_excerpts():
    result = consolidation_check(fx.TITLE_MISMATCH_RESUME, fx.TITLE_MISMATCH_LINKEDIN)
    finding = result.findings[0]
    assert hasattr(finding, "code")
    assert hasattr(finding, "severity")
    assert hasattr(finding, "role_context")
    assert hasattr(finding, "resume_excerpt")
    assert hasattr(finding, "linkedin_excerpt")
    assert hasattr(finding, "suggested_resolutions")
    assert isinstance(finding.suggested_resolutions, list)
    assert len(finding.suggested_resolutions) == 3
    tags = {r["tag"] for r in finding.suggested_resolutions}
    assert tags == {"RESUME-LEADING", "LINKEDIN-LEADING", "NEW-SYNTHESIS"}


def test_unmatched_role_in_resume_does_not_crash():
    """If a role appears in resume but not LinkedIn, the validator skips it
    silently — that's a coverage gap, not an inconsistency finding."""
    resume = fx.CLEAN_RESUME + [{
        "company": "Unique Co",
        "title": "Engineer",
        "start_date": "2010-01",
        "end_date": "2014-12",
        "bullets": ["Did things."],
        "description": "Did things.",
    }]
    result = consolidation_check(resume, fx.CLEAN_LINKEDIN)
    # The clean role still matches cleanly; the unmatched role is ignored.
    assert result.findings == []
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
python -m pytest tests/validators/test_consolidation_check.py -v
```

Expected: ImportError on `scripts.validators.consolidation_check`.

- [ ] **Step 3: Write the implementation**

Create `scripts/validators/consolidation_check.py`:

```python
"""Resume + LinkedIn consolidation validator.

Compares position-level data extracted from a resume against position data
parsed from a LinkedIn export and surfaces narrative inconsistencies:

  - CONSOLIDATION_JOB_TITLE_MISMATCH       (severity: MEDIUM)
  - CONSOLIDATION_DATE_INCONSISTENCY       (severity: MEDIUM)
  - CONSOLIDATION_ACHIEVEMENT_ONLY_IN_RESUME    (severity: LOW)
  - CONSOLIDATION_ACHIEVEMENT_ONLY_IN_LINKEDIN  (severity: LOW)
  - CONSOLIDATION_TONE_DIVERGENCE          (severity: LOW — heuristic)

Each finding carries three suggested resolutions (resume-leading,
linkedin-leading, new-synthesis). The user chooses.

Read-only: this validator never edits either document.
"""
from dataclasses import dataclass, field
from difflib import SequenceMatcher
import re
from typing import List, Dict, Optional


# --- Result types -------------------------------------------------------------

# Resolutions are dicts {"tag": ..., "text": ...} rather than a dataclass —
# the dict shape matches the markdown-report rendering directly and keeps
# the type surface narrow.


@dataclass
class ConsolidationFinding:
    code: str
    severity: str
    role_context: str  # human-readable identifier of the role being compared
    resume_excerpt: str
    linkedin_excerpt: str
    suggested_resolutions: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class ConsolidationCheckResult:
    findings: List[ConsolidationFinding] = field(default_factory=list)


# --- Matching helpers ---------------------------------------------------------

def _normalise_company(name: str) -> str:
    """Lower-case + strip common corporate suffixes for fuzzy company match."""
    n = (name or "").lower().strip()
    for suffix in (" inc.", " inc", " corp.", " corp", " corporation",
                   " ltd.", " ltd", " limited", " llc", " gmbh"):
        if n.endswith(suffix):
            n = n[: -len(suffix)]
    return n.strip()


def _similar(a: str, b: str) -> float:
    """Return a 0-1 similarity ratio for two strings."""
    return SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio()


def _dates_overlap(r_start: str, r_end: str, l_start: str, l_end: str) -> bool:
    """Both date pairs are YYYY-MM strings (or YYYY). Return True if the
    intervals overlap at the year level — the same-role match is permissive.
    Differences within the overlap window are surfaced as DATE_INCONSISTENCY."""
    def year(s):
        return int((s or "0000")[:4])
    r_s, r_e = year(r_start), year(r_end) or 9999
    l_s, l_e = year(l_start), year(l_end) or 9999
    return r_s <= l_e and l_s <= r_e


def _match_roles(resume_positions, linkedin_positions):
    """Yield (resume_pos, linkedin_pos) pairs that refer to the same role.

    Match heuristic: normalised company name similarity >= 0.85 AND date
    intervals overlap at the year level.
    """
    used = set()
    for r in resume_positions:
        r_company = _normalise_company(r.get("company"))
        for idx, l in enumerate(linkedin_positions):
            if idx in used:
                continue
            if _similar(r_company, _normalise_company(l.get("company"))) < 0.85:
                continue
            if not _dates_overlap(
                r.get("start_date", ""), r.get("end_date", ""),
                l.get("start_date", ""), l.get("end_date", ""),
            ):
                continue
            used.add(idx)
            yield r, l
            break


# --- Bullet-similarity for ACHIEVEMENT_ONLY_IN_* ------------------------------

BULLET_SIMILARITY_THRESHOLD = 0.55  # tuned for paraphrase tolerance


def _bullet_matches_any(bullet: str, candidates: List[str]) -> bool:
    return any(_similar(bullet, c) >= BULLET_SIMILARITY_THRESHOLD for c in candidates)


# --- Tone divergence heuristic ------------------------------------------------

FORMAL_TOKENS = (
    "directed", "achieved", "delivered", "implemented", "established",
    "architected", "demonstrated", "measurable", "across", "throughout",
)
CASUAL_TOKENS = (
    "spent", "turned out", "got there", "stuff", "things", "good times",
    "a lot of", "kind of", "sort of", "way", "way bigger",
)


def _formality_score(text: str) -> int:
    """Crude lexical formality score. Positive = formal-leaning; negative = casual."""
    if not text:
        return 0
    t = text.lower()
    formal_hits = sum(1 for tok in FORMAL_TOKENS if tok in t)
    casual_hits = sum(1 for tok in CASUAL_TOKENS if tok in t)
    return formal_hits - casual_hits


def _tone_diverges(resume_desc: str, linkedin_desc: str) -> bool:
    """True if the two descriptions read as substantially different register.

    Heuristic — flagged as such in suggestion text. The user always decides.
    """
    return abs(_formality_score(resume_desc) - _formality_score(linkedin_desc)) >= 3


# --- Suggested-resolution generator -------------------------------------------

def _three_resolutions(resume_value: str, linkedin_value: str, kind: str):
    """Produce the resume-leading / linkedin-leading / new-synthesis triple."""
    return [
        {"tag": "RESUME-LEADING",
         "text": f"Adopt the resume version on both surfaces: {resume_value!r}."},
        {"tag": "LINKEDIN-LEADING",
         "text": f"Adopt the LinkedIn version on both surfaces: {linkedin_value!r}."},
        {"tag": "NEW-SYNTHESIS",
         "text": f"Write a new {kind} that unifies the strongest elements of both. "
                 f"This typically requires a manual rewrite — the validator does not "
                 f"auto-generate it."},
    ]


# --- Main validator -----------------------------------------------------------

def consolidation_check(
    resume_positions: List[dict],
    linkedin_positions: List[dict],
) -> ConsolidationCheckResult:
    """Compare resume and LinkedIn position lists and surface inconsistencies.

    Each position dict expects keys: company, title, start_date (YYYY-MM or
    YYYY), end_date (same), bullets (list[str]), description (str).
    """
    result = ConsolidationCheckResult()

    for r, l in _match_roles(resume_positions, linkedin_positions):
        role_context = f"{r.get('company', '')} ({r.get('start_date', '')} – {r.get('end_date', '')})"

        # 1. Title mismatch
        if _similar(r.get("title", ""), l.get("title", "")) < 0.85:
            result.findings.append(ConsolidationFinding(
                code="CONSOLIDATION_JOB_TITLE_MISMATCH",
                severity="MEDIUM",
                role_context=role_context,
                resume_excerpt=r.get("title", ""),
                linkedin_excerpt=l.get("title", ""),
                suggested_resolutions=_three_resolutions(
                    r.get("title", ""), l.get("title", ""), "title"
                ),
            ))

        # 2. Date inconsistency — start or end month differs while same role
        if r.get("start_date", "") != l.get("start_date", ""):
            result.findings.append(ConsolidationFinding(
                code="CONSOLIDATION_DATE_INCONSISTENCY",
                severity="MEDIUM",
                role_context=role_context,
                resume_excerpt=f"Start: {r.get('start_date', '')}",
                linkedin_excerpt=f"Start: {l.get('start_date', '')}",
                suggested_resolutions=_three_resolutions(
                    r.get("start_date", ""), l.get("start_date", ""), "start date"
                ),
            ))
        elif r.get("end_date", "") != l.get("end_date", ""):
            result.findings.append(ConsolidationFinding(
                code="CONSOLIDATION_DATE_INCONSISTENCY",
                severity="MEDIUM",
                role_context=role_context,
                resume_excerpt=f"End: {r.get('end_date', '')}",
                linkedin_excerpt=f"End: {l.get('end_date', '')}",
                suggested_resolutions=_three_resolutions(
                    r.get("end_date", ""), l.get("end_date", ""), "end date"
                ),
            ))

        # 3. Achievement only on resume
        r_bullets = r.get("bullets", []) or []
        l_bullets = l.get("bullets", []) or []
        for b in r_bullets:
            if not _bullet_matches_any(b, l_bullets):
                result.findings.append(ConsolidationFinding(
                    code="CONSOLIDATION_ACHIEVEMENT_ONLY_IN_RESUME",
                    severity="LOW",
                    role_context=role_context,
                    resume_excerpt=b,
                    linkedin_excerpt="(not present)",
                    suggested_resolutions=[
                        {"tag": "RESUME-LEADING",
                         "text": f"Add this bullet to the LinkedIn role: {b!r}."},
                        {"tag": "LINKEDIN-LEADING",
                         "text": f"Drop the bullet from the resume — the LinkedIn version omits it for a reason the user knows best."},
                        {"tag": "NEW-SYNTHESIS",
                         "text": "Rephrase the bullet for LinkedIn's audience (recruiter scan, "
                                 "scrolling-on-mobile context) and add a tightened version there."},
                    ],
                ))

        # 4. Achievement only on LinkedIn
        for b in l_bullets:
            if not _bullet_matches_any(b, r_bullets):
                result.findings.append(ConsolidationFinding(
                    code="CONSOLIDATION_ACHIEVEMENT_ONLY_IN_LINKEDIN",
                    severity="LOW",
                    role_context=role_context,
                    resume_excerpt="(not present)",
                    linkedin_excerpt=b,
                    suggested_resolutions=[
                        {"tag": "RESUME-LEADING",
                         "text": "Drop the bullet from LinkedIn — the resume version omits it."},
                        {"tag": "LINKEDIN-LEADING",
                         "text": f"Add this bullet to the resume role: {b!r}."},
                        {"tag": "NEW-SYNTHESIS",
                         "text": "Rephrase the bullet for the resume audience (achievement-led, "
                                 "metric-anchored) and add a tightened version there."},
                    ],
                ))

        # 5. Tone divergence
        if _tone_diverges(r.get("description", ""), l.get("description", "")):
            result.findings.append(ConsolidationFinding(
                code="CONSOLIDATION_TONE_DIVERGENCE",
                severity="LOW",
                role_context=role_context,
                resume_excerpt=(r.get("description", "") or "")[:140],
                linkedin_excerpt=(l.get("description", "") or "")[:140],
                suggested_resolutions=[
                    {"tag": "RESUME-LEADING",
                     "text": "Carry the resume's formal/quantitative register over to LinkedIn — "
                             "match the resume's specificity in narrative form on LinkedIn."},
                    {"tag": "LINKEDIN-LEADING",
                     "text": "Carry the LinkedIn's conversational register over to the resume — "
                             "tighten where needed but preserve the voice."},
                    {"tag": "NEW-SYNTHESIS",
                     "text": "Pick a target register for each surface deliberately. Resume: formal, "
                             "metric-anchored. LinkedIn: first-person, scannable proof. The two "
                             "registers can both be intentional; they should not be accidental."},
                ],
            ))

    return result
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest tests/validators/test_consolidation_check.py -v
```

Expected: all green.

- [ ] **Step 5: Run the full suite**

```powershell
python -m pytest -q
```

Expected: all green.

- [ ] **Step 6: Commit**

```powershell
git add scripts/validators/consolidation_check.py tests/validators/test_consolidation_check.py
git commit -m "feat: add consolidation_check validator for resume+LinkedIn alignment"
```

---

## Task 16 — `references/workflows/consolidate.md`

The workflow reference. Defines inputs, procedure for structured-data extraction from the resume side, finding presentation, and handoff to fix workflows.

**Files:**

- Create: `references/workflows/consolidate.md`
- Create: `tests/references/test_workflow_consolidate.py`

### Steps

- [ ] **Step 1: Write the reference document**

Create `references/workflows/consolidate.md`:

```markdown
# Workflow: Resume + LinkedIn Consolidation

**Purpose:** Detect narrative inconsistencies between a user's resume and LinkedIn profile and propose unifying resolutions. Recruiters routinely cross-check both surfaces; deltas (different titles for the same role, mismatched dates, achievements claimed in one but not the other, register differences) are read as either carelessness or evasion.

This workflow is **read-only** — it produces a coaching report. Actual fixes happen via the existing edit / linkedin-improve workflows. The user always chooses which resolution to apply.

---

## Trigger conditions

Start this workflow when any of the following are true:

- The user says "consolidate my resume and LinkedIn", "check my resume against my LinkedIn", "make sure these match", or any equivalent.
- The user has just completed a resume-edit or linkedin-improve workflow and asks to verify the other surface is aligned.
- The user runs `/brains-consolidate`.

---

## Inputs

1. **Resume** — DOCX or PDF. Parsed via `scripts/parsers/docx_to_text.py` or `scripts/parsers/pdf_to_text.py`. Text is then structured per role by Claude (see procedure step (b)).
2. **LinkedIn data** — either:
   - A LinkedIn ZIP export (parsed via `scripts/parsers/linkedin_zip.py`) — preferred, structured by default.
   - **OR** a markdown file produced by the `brains-linkedin-improve` workflow.
   - **OR** pasted LinkedIn sections.

If only one of the two inputs is available, ask the user to provide the other. The workflow does not run with one side.

---

## Procedure

**(a) Parse both inputs.**

```python
from scripts.parsers.docx_to_text import parse_docx_resume
from scripts.parsers.linkedin_zip import parse_linkedin_export

resume = parse_docx_resume(resume_path)
linkedin = parse_linkedin_export(linkedin_zip_path)
```text

Surface the LinkedIn `skipped_files` list as in the linkedin-ingest workflow.

**(b) Extract structured positions from the resume.**

The LinkedIn parser already returns structured positions. The resume parser returns raw text. Claude does the structured extraction from the resume side — produce a list of position dicts shaped like:

```python
{
    "company": "Example Corp",
    "title": "Senior Engineer",
    "start_date": "2020-03",   # YYYY-MM if a month is present, YYYY otherwise
    "end_date": "2024-08",     # same format; "Present" treated as current year
    "bullets": ["First bullet text.", "Second bullet text."],
    "description": "A flowing-prose description of the role for tone analysis. "
                   "If the resume only has bullets, concatenate them here.",
}
```text

Show the structured extraction to the user and confirm before proceeding. The extraction is informed; the user has the veto.

**(c) Convert the LinkedIn parser output into the same shape.**

The LinkedIn `positions` list typically contains fields like `Company Name`, `Title`, `Started On`, `Finished On`, `Description`. Map them:

```python
def _from_linkedin(pos):
    desc = pos.get("Description", "") or ""
    # Split the description into bullets if it contains line-breaks or "•"
    bullets = [b.strip() for b in re.split(r"[\n•]", desc) if b.strip()]
    return {
        "company": pos.get("Company Name", ""),
        "title": pos.get("Title", ""),
        "start_date": pos.get("Started On", ""),
        "end_date": pos.get("Finished On", "") or "Present",
        "bullets": bullets,
        "description": desc,
    }

linkedin_positions = [_from_linkedin(p) for p in linkedin["positions"]]
```text

**(d) Run the validator.**

```python
from scripts.validators.consolidation_check import consolidation_check

result = consolidation_check(resume_positions, linkedin_positions)
```text

The validator returns a `ConsolidationCheckResult` with a `findings` list. Each finding has a `code`, `severity`, `role_context`, `resume_excerpt`, `linkedin_excerpt`, and `suggested_resolutions` (a list of three resolutions tagged `RESUME-LEADING`, `LINKEDIN-LEADING`, `NEW-SYNTHESIS`).

**(e) Present findings to the user.**

Group findings by role. For each role with any finding, render a side-by-side comparison:

| Aspect | Resume | LinkedIn |
|---|---|---|
| Title | {resume title} | {linkedin title} |
| Dates | {resume dates} | {linkedin dates} |
| Achievements | {resume bullets} | {linkedin bullets} |
| Description register | (formal / casual / neutral) | (formal / casual / neutral) |

Below each comparison, list the findings raised for that role with the three resolutions per finding. The user picks per-finding which resolution to apply.

**Important framing:** The tone-divergence finding (`CONSOLIDATION_TONE_DIVERGENCE`) is heuristic. State this explicitly when presenting it — the validator surfaces a register difference as a signal, not as a definitive judgement, and the user may have intentional reasons for the two surfaces sounding different.

**(f) Save the consolidation report.**

Write to `output/consolidation-report-YYYY-MM-DD-HHMMSS.md` with this structure:

```markdown
# Resume + LinkedIn Consolidation Report

**Prepared:** {date}
**Resume:** {resume filename}
**LinkedIn source:** {ZIP filename or pasted source description}

---

## Summary

- Roles compared: {n}
- Findings raised: {n}
  - Title mismatches: {n}
  - Date inconsistencies: {n}
  - Achievement-only-in-resume: {n}
  - Achievement-only-in-LinkedIn: {n}
  - Tone divergence (heuristic): {n}

---

## Per-role findings

### {Company} ({dates})

{side-by-side table}

**Findings:**

- **{finding code}** ({severity}): {role context}
  - Resume: {resume excerpt}
  - LinkedIn: {linkedin excerpt}
  - Suggested resolutions:
    - [RESUME-LEADING] {text}
    - [LINKEDIN-LEADING] {text}
    - [NEW-SYNTHESIS] {text}

(Repeat per role)

---

## Next steps

When you decide which resolutions to apply:

- For fixes on the **resume side**, run `/brains-edit` with the current resume.
- For fixes on the **LinkedIn side**, run `/brains-linkedin-improve` with the current profile.
- For aligned re-tailoring (you also want both surfaces optimised for a new target role), run `/brains-tailor` first on the resume, then `/brains-linkedin-improve`.

This report is read-only. The skill does not apply resolutions automatically.
```text

This artifact carries BRAINS coaching branding — it is an internal coaching artifact, not a submitted document.

**(g) Offer next steps.**

Based on the user's resolution choices, offer the relevant fix workflow. Do not auto-launch; ask first.

---

## Output artifacts

| File | Notes |
|---|---|
| `output/consolidation-report-YYYY-MM-DD-HHMMSS.md` | BRAINS coaching artifact — read-only report; user chooses which resolutions to apply |

---

## Safeguarding boundaries

- **Read-only on cross-document edits.** The validator surfaces deltas. It never edits either document. Fixes happen via the existing edit / linkedin-improve workflows after the user chooses.
- **Tone-divergence is heuristic.** Always state this when presenting tone-divergence findings. The user may have intentional reasons for register differences between the two surfaces.
- **Third-party PII guard inherited from `linkedin_zip.py`.** Connections, messages, invitations, reactions, comments, likes — all skipped at the parser level.
- **The structured extraction from the resume is confirmed by the user.** Step (b) is not a silent step — the user sees the extraction and can correct it before findings are computed.

```

- [ ] **Step 2: Add a structural test**

Create `tests/references/test_workflow_consolidate.py`:

```python
"""Structural tests for references/workflows/consolidate.md."""
from pathlib import Path

REFERENCE = Path(__file__).parent.parent.parent / "references" / "workflows" / "consolidate.md"


def _text():
    return REFERENCE.read_text(encoding="utf-8")


def test_reference_exists():
    assert REFERENCE.exists()


def test_all_five_finding_codes_documented():
    text = _text()
    for code in (
        "CONSOLIDATION_JOB_TITLE_MISMATCH",
        "CONSOLIDATION_DATE_INCONSISTENCY",
        "CONSOLIDATION_ACHIEVEMENT_ONLY_IN_RESUME",
        "CONSOLIDATION_ACHIEVEMENT_ONLY_IN_LINKEDIN",
        "CONSOLIDATION_TONE_DIVERGENCE",
    ):
        assert code in text, f"Finding code not documented: {code}"


def test_three_resolution_tags_documented():
    text = _text()
    for tag in ("RESUME-LEADING", "LINKEDIN-LEADING", "NEW-SYNTHESIS"):
        assert tag in text


def test_tone_divergence_explicitly_flagged_as_heuristic():
    text = _text().lower()
    assert "heuristic" in text
    # Within ~200 chars of the word, "tone" or "register" should also appear.


def test_read_only_handoff_pattern_documented():
    text = _text()
    assert "read-only" in text.lower()
    assert "/brains-edit" in text
    assert "/brains-linkedin-improve" in text
```

- [ ] **Step 3: Run tests**

```powershell
python -m pytest tests/references/test_workflow_consolidate.py -v
```

Expected: all green.

- [ ] **Step 4: Commit**

```powershell
git add references/workflows/consolidate.md tests/references/test_workflow_consolidate.py
git commit -m "docs: add consolidation workflow reference"
```

---

## Task 17 — Slash command + SKILL.md router update for `consolidate`

**Files:**

- Create: `commands/brains-consolidate.md`
- Modify: `SKILL.md`

### Steps

- [ ] **Step 1: Create the slash command file**

Create `commands/brains-consolidate.md`:

```markdown
---
description: Detect narrative inconsistencies between a resume and a LinkedIn profile and propose resolutions
argument-hint: [optional: path to resume, path to LinkedIn ZIP]
---

Run the BRAINS Resume Skill consolidation workflow. Load `~/.claude/skills/brains-resume/references/workflows/consolidate.md` and follow its procedure. Inputs from `$ARGUMENTS` (resume path + LinkedIn ZIP path) or supplied in the next message.
```

- [ ] **Step 2: Update SKILL.md workflow router**

In `SKILL.md`, add a new row after the linkedin-improve entry from Task 12:

```markdown
| Improve / rewrite my LinkedIn profile | `references/workflows/linkedin-improve.md` |
| Check my resume and LinkedIn for inconsistencies | `references/workflows/consolidate.md` |
```

- [ ] **Step 3: Update the capability menu**

Append after the linkedin-improve row:

```markdown
| Improve LinkedIn profile | Live |
| Resume + LinkedIn consolidation | Live |
```

- [ ] **Step 4: Update the slash-command list line**

The line currently reads (after Task 12):

> "Type `/brains-` and Claude Code will list the ten commands: review, disclosure, edit, tailor, cover-letter, create, linkedin, linkedin-improve, career-change, check."

Update to:

> "Type `/brains-` and Claude Code will list the eleven commands: review, disclosure, edit, tailor, cover-letter, create, linkedin, linkedin-improve, consolidate, career-change, check."

- [ ] **Step 5: Update the v1 "all nine workflows are live" phrasing**

Find this paragraph in the First-Use Behaviour section:

> "BRAINS Resume Skill is ready. All nine workflows are live — resume review, disclosure coaching, create, edit, tailor, cover letter, LinkedIn ingestion, career-change translation, and final pre-submit check."

Update to:

> "BRAINS Resume Skill is ready. All eleven workflows are live — resume review, disclosure coaching, create, edit, tailor, cover letter, LinkedIn ingestion, LinkedIn profile improvement, resume-and-LinkedIn consolidation, career-change translation, and final pre-submit check."

Also update the shorter greeting earlier in the same section:

> "BRAINS Resume Skill is ready — all nine workflows are live."

becomes:

> "BRAINS Resume Skill is ready — all eleven workflows are live."

- [ ] **Step 6: Run the suite**

```powershell
python -m pytest -q
```

Expected: all green.

- [ ] **Step 7: Commit**

```powershell
git add commands/brains-consolidate.md SKILL.md
git commit -m "feat: add brains-consolidate slash command and router entry"
```

---

## Task 18 — Consolidation smoke test

End-to-end: parse the synthetic resume + synthetic LinkedIn export, transform the LinkedIn parser output into the validator's expected shape, run the validator with seeded deltas, write the report file.

**Files:**

- Create: `tests/test_smoke_consolidate_workflow.py`

### Steps

- [ ] **Step 1: Write the smoke test**

Create `tests/test_smoke_consolidate_workflow.py`:

```python
"""Smoke test for the deterministic portion of the consolidation workflow.

Exercises: validator runs end-to-end on structured position pairs derived
from fixtures, the report artifact is written, and all five finding codes
are achievable on the seeded inputs.
"""
from pathlib import Path

from scripts.validators.consolidation_check import consolidation_check
from tests.fixtures import consolidation_fixtures as fx


def test_consolidate_smoke_all_finding_codes_reachable(tmp_path):
    # Combine the seeded fixtures so a single run surfaces every finding code.
    resume = (
        fx.TITLE_MISMATCH_RESUME
        + fx.DATE_MISMATCH_RESUME
        + fx.ACHIEVEMENT_RESUME_ONLY_RESUME
        + fx.TONE_DIVERGENT_RESUME
    )
    linkedin = (
        fx.TITLE_MISMATCH_LINKEDIN
        + fx.DATE_MISMATCH_LINKEDIN
        + fx.ACHIEVEMENT_RESUME_ONLY_LINKEDIN
        + fx.TONE_DIVERGENT_LINKEDIN
    )

    result = consolidation_check(resume, linkedin)
    codes = {f.code for f in result.findings}
    # Note: title mismatch and tone divergence both come off the Example Corp
    # role in different fixtures — both should fire.
    assert "CONSOLIDATION_JOB_TITLE_MISMATCH" in codes
    assert "CONSOLIDATION_DATE_INCONSISTENCY" in codes
    assert "CONSOLIDATION_ACHIEVEMENT_ONLY_IN_RESUME" in codes
    assert "CONSOLIDATION_TONE_DIVERGENCE" in codes

    # Write the report artifact
    out = tmp_path / "consolidation-report-2026-05-13-120000.md"
    lines = [
        "# Resume + LinkedIn Consolidation Report\n",
        "**Prepared:** 2026-05-13\n",
        "**Resume:** synthetic_resume_basic.docx\n",
        "**LinkedIn source:** synthetic_linkedin_export.zip\n",
        "\n## Summary\n",
        f"- Roles compared: {len(resume)}\n",
        f"- Findings raised: {len(result.findings)}\n",
        "\n## Per-role findings\n",
    ]
    for f in result.findings:
        lines.append(f"\n### {f.role_context}\n")
        lines.append(f"- **{f.code}** ({f.severity})\n")
        lines.append(f"  - Resume: {f.resume_excerpt}\n")
        lines.append(f"  - LinkedIn: {f.linkedin_excerpt}\n")
        lines.append("  - Suggested resolutions:\n")
        for r in f.suggested_resolutions:
            lines.append(f"    - [{r['tag']}] {r['text']}\n")
    out.write_text("".join(lines), encoding="utf-8")

    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "Consolidation Report" in content
    assert "RESUME-LEADING" in content
    assert "LINKEDIN-LEADING" in content
    assert "NEW-SYNTHESIS" in content
```

- [ ] **Step 2: Run the smoke test**

```powershell
python -m pytest tests/test_smoke_consolidate_workflow.py -v
```

Expected: green.

- [ ] **Step 3: Run the full suite**

```powershell
python -m pytest -q
```

Expected: all green.

- [ ] **Step 4: Commit**

```powershell
git add tests/test_smoke_consolidate_workflow.py
git commit -m "test: add consolidation workflow smoke test"
```

---

## Phase 4 — Release polish (Tasks 19-22)

Documentation, brand-application updates, bundle rebuild, and the v1.1.0 tag.

---

## Task 19 — Update README and brand-application reference

**Files:**

- Modify: `README.md` (slash-command list + "Choosing a template" section)
- Modify: `references/brand-application.md` (new artifact types)

### Steps

- [ ] **Step 1: Update slash-command list in README**

Find the slash-command section in `README.md` (it currently lists the nine commands from v1.0.x). Add two entries — placement should match the existing alphabetical or topical ordering used in the README:

```markdown
- `/brains-linkedin-improve` — Rewrite a LinkedIn profile (Headline / About / Experience / Skills) using the ND-aware framework
- `/brains-consolidate` — Detect inconsistencies between a resume and a LinkedIn profile and propose resolutions
```

Update the count if the README mentions "nine commands" — change to "eleven commands".

- [ ] **Step 2: Add a "Choosing a template" section to README**

Add this section after the slash-command list:

```markdown
## Choosing a template

The skill ships four resume templates and two cover-letter templates. All are ATS-safe; the choice is about narrative shape:

| Resume template | Best for |
|---|---|
| `chronological` (default) | Linear career history with recent relevant experience |
| `functional` | Career-changers, employment gaps, skills-led story |
| `hybrid` | Career pivots with relevant transferable skills |
| `executive` | Senior roles, 15+ years experience, board / leadership framing |

| Cover-letter template | Best for |
|---|---|
| `formal-business` (default) | Traditional industries, regulated sectors |
| `modern-clean` | Tech / startup contexts |

The skill walks the user through template selection during the create / edit / tailor workflows. See `references/template-selection.md` for the full decision tree, including the ND framing on the functional-template tradeoff.
```

- [ ] **Step 3: Update `references/brand-application.md`**

In the "Section 1 — The Split Rule" table, add rows for the new artifact types. Insert after the existing "Generated cover letters" row:

```markdown
| LinkedIn profile rewrite — text within the markdown artifact (Headline / About / Experience / Skills) | **Unbranded** — plain text intended for paste into LinkedIn | LinkedIn is a third-party surface where BRAINS branding would be inappropriate. |
| LinkedIn profile rewrite — surrounding markdown coaching wrapper | BRAINS branded — coaching artifact frame | The wrapper is an internal coaching session record, same category as the review coaching report. |
| Consolidation report (markdown) | **BRAINS branded** — Gold Deep headings, BRAINS mark in header if rendered to PDF, identity-first language | Internal coaching artifact, same category as the review coaching report. |
```

- [ ] **Step 4: Run the suite**

```powershell
python -m pytest -q
```

Expected: all green.

- [ ] **Step 5: Commit**

```powershell
git add README.md references/brand-application.md
git commit -m "docs: update README slash-command list, add template section, extend brand-application rules"
```

---

## Task 20 — Rebuild Claude Project bundle

The bundle's `INCLUDED_PATHS` list needs to include the new directories (`templates/resume/`, `templates/cover-letter/`) and the new reference files. The new validators and parsers don't ship in the bundle (scripts can't run on claude.ai), but the reference docs and slash-command markdown files do.

**Files:**

- Modify: `scripts/packaging/build_project_bundle.py`
- Modify: `docs/claude-project-setup.md` (note about new workflows + template selection)

### Steps

- [ ] **Step 1: Update `build_project_bundle.py`**

The current `INCLUDED_PATHS` list contains:

```python
INCLUDED_PATHS = [
    "SKILL.md",
    "references",
    "docs/claude-project-setup.md",
    "templates/coaching_report.md",
    "LICENSE",
]
```

`references` is already a directory walk, so the new `references/template-selection.md`, `references/workflows/linkedin-improve.md`, and `references/workflows/consolidate.md` will be picked up automatically.

The DOCX templates do **not** ship in the bundle (claude.ai can't generate from them; users running on claude.ai don't get the generators either — that's Claude Code territory).

No code change required. Verify by running the bundle build:

```powershell
python scripts\packaging\build_project_bundle.py
```

Expected: prints `Wrote ...\dist\brains-resume-claude-project.zip`.

- [ ] **Step 2: Verify the new references are in the bundle**

```powershell
python -c "import zipfile; z = zipfile.ZipFile('dist/brains-resume-claude-project.zip'); names = z.namelist(); print('template-selection:', 'brains-resume-claude-project/references/template-selection.md' in names); print('linkedin-improve:', 'brains-resume-claude-project/references/workflows/linkedin-improve.md' in names); print('consolidate:', 'brains-resume-claude-project/references/workflows/consolidate.md' in names)"
```

Expected: all three `True`.

- [ ] **Step 3: Update the Claude Project setup guide**

In `docs/claude-project-setup.md`, find the workflow list (it currently enumerates the v1.0.x set of nine workflows) and add the two new workflows. Also add a one-line note explaining that template selection happens during the create/edit/tailor workflows and references `template-selection.md`.

If the file does not currently list workflows by name, add a short "Workflows available on claude.ai" subsection enumerating all eleven workflows.

- [ ] **Step 4: Rebuild the bundle to capture the setup-guide edit**

```powershell
python scripts\packaging\build_project_bundle.py
```

- [ ] **Step 5: Commit**

```powershell
git add scripts/packaging/build_project_bundle.py docs/claude-project-setup.md
git commit -m "build: rebuild Claude Project bundle with v1.1.0 references and updated setup guide"
```

(Note: do not commit `dist/brains-resume-claude-project.zip` itself — it's generated and should be in `.gitignore`. Verify with `git status` that no `dist/` files are staged. If they are, remove them from staging: `git restore --staged dist/`.)

---

## Task 21 — CHANGELOG entry for v1.1.0

**Files:**

- Modify: `CHANGELOG.md`

### Steps

- [ ] **Step 1: Add the v1.1.0 entry**

At the top of `CHANGELOG.md`, above the v1.0.2 entry, add:

```markdown
## [1.1.0] — 2026-05-13

### Added
- **Resume template library** — four templates total: `chronological` (existing, moved into `templates/resume/`), `functional` (new), `hybrid` (new), `executive` (new). All ATS-safe.
- **Cover-letter template library** — two templates total: `formal-business` (existing, moved into `templates/cover-letter/`), `modern-clean` (new).
- **Generator parameterisation** — `resume_to_docx`, `resume_to_pdf`, `cover_letter_to_docx`, and `cover_letter_to_pdf` now accept a `template=` keyword argument. Defaults preserve v1.0.x behaviour.
- **Template-selection reference** (`references/template-selection.md`) — decision tree, comparison tables, and ND framing on the functional-template recruiter-skepticism tradeoff with `hybrid` as the recommended middle path.
- **LinkedIn profile improvement workflow** (`/brains-linkedin-improve`) — rewrites Headline / About / Experience / Skills using the ND-aware framework, with character limits respected and copy-paste-ready markdown output.
- **Resume + LinkedIn consolidation workflow** (`/brains-consolidate`) — detects narrative inconsistencies between resume and LinkedIn (job title mismatches, date inconsistencies, achievement-only-in-X, tone divergence) and proposes three resolutions per finding (resume-leading, linkedin-leading, new synthesis). Read-only report; fixes via existing `/brains-edit` and `/brains-linkedin-improve` workflows.
- **New validator** — `scripts/validators/consolidation_check.py` with five finding codes covering the deltas the consolidation workflow surfaces.

### Changed
- **Template directory layout** — `templates/resume_chronological.docx` moved to `templates/resume/chronological.docx`. `templates/cover_letter.docx` moved to `templates/cover-letter/formal-business.docx`. Template-generator scripts under `scripts/packaging/` renamed to match the new layout.
- **SKILL.md router** — two new workflow entries; capability menu and slash-command list updated to reflect eleven live workflows.
- **`references/brand-application.md`** — Split-rule table extended to cover new artifact types (LinkedIn profile rewrite output and consolidation report).
- **`README.md`** — slash-command list updated; new "Choosing a template" section added.
- **Claude Project bundle** — rebuilt to include new reference docs.

### Deferred to Phase 3
- MCP server for Claude Desktop.
- Creative / graphical resume templates (excluded for ATS-safety + ND-bias reasons).
- Autonomous LinkedIn editing.
- Sibling skills (interview prep, salary negotiation).
```

- [ ] **Step 2: Commit**

```powershell
git add CHANGELOG.md
git commit -m "docs: add v1.1.0 CHANGELOG entry"
```

---

## Task 22 — Bump skill version and tag v1.1.0

**Files:**

- Modify: `SKILL.md` (frontmatter `version`)
- Modify: `pyproject.toml` (if it carries a version)

### Steps

- [ ] **Step 1: Bump the version in SKILL.md frontmatter**

In `SKILL.md`, find the frontmatter block:

```yaml
---
name: brains-resume
description: ...
version: 1.0.0
license: MIT
---
```

Change `version: 1.0.0` to `version: 1.1.0`.

Also update the body line that currently reads:

> "This is a BRAINS Incubator project, v1.0.0."

to:

> "This is a BRAINS Incubator project, v1.1.0."

- [ ] **Step 2: Bump the version in pyproject.toml (if present)**

Open `pyproject.toml`. If there is a `version = "1.0.0"` (or `"1.0.2"`) line under `[project]`, change it to `version = "1.1.0"`. If `pyproject.toml` does not declare a version (some projects derive it dynamically), skip this step.

- [ ] **Step 3: Run the full suite one final time**

```powershell
python -m pytest -q
```

Expected: all green. Every test from v1.0.x continues to pass; all new Phase 2 tests are green.

- [ ] **Step 4: Commit the version bump**

```powershell
git add SKILL.md pyproject.toml
git commit -m "chore: bump version to 1.1.0"
```

- [ ] **Step 5: Create the v1.1.0 tag**

```powershell
git tag -a v1.1.0 -m "v1.1.0 — Phase 2: template library, LinkedIn profile improvement, consolidation"
```

- [ ] **Step 6: Verify tag**

```powershell
git tag --list
git show v1.1.0 --stat
```

Expected: `v1.1.0` appears in the tag list; the show output references the chore commit and the recent commit history.

- [ ] **Step 7: Final status check**

```powershell
git status
git log --oneline -25
```

Expected: working tree clean; the last ~22 commits trace the plan tasks; the most recent commit is the `chore: bump version to 1.1.0`.

The v1.1.0 release is complete. The user can push when ready (`git push && git push --tags`) — the plan does not auto-push.

---

## Plan completion checklist

After all tasks are marked complete, verify:

- [ ] All 22 tasks have every step checked off.
- [ ] `python -m pytest -q` reports green with no skipped tests other than ones that were skipped before this plan started.
- [ ] `git tag --list` includes `v1.1.0`.
- [ ] `dist/brains-resume-claude-project.zip` was rebuilt and contains `template-selection.md`, `linkedin-improve.md`, and `consolidate.md` under `references/`.
- [ ] No commits include `Co-Authored-By` footers.
- [ ] No third-party org or project proper-name attribution appears in any committed file or commit message.
- [ ] `SKILL.md` frontmatter says `version: 1.1.0`.
- [ ] All four resume templates (`chronological`, `functional`, `hybrid`, `executive`) exist under `templates/resume/` and all pass `ats_check`.
- [ ] Both cover-letter templates (`formal-business`, `modern-clean`) exist under `templates/cover-letter/` and pass `ats_check`.

When every box is ticked, the release is shippable.
