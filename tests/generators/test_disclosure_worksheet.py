"""Tests for scripts/generators/disclosure_worksheet.py."""
from pathlib import Path

import pdfplumber
import pytest


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    monkeypatch.setenv("BRAINS_OUTPUTS_DIR", str(tmp_path / "outputs"))
    return tmp_path


@pytest.fixture
def candidate_and_session(isolated):
    from scripts.tracker.candidates import create_candidate
    from scripts.tracker.disclosure import create_session
    cid = create_candidate(
        first_name="Matthew", last_name="Gell",
        focus_areas=[], healthy_weekly_rate=None, pacing_notes=None,
    )
    sid = create_session(
        candidate_id=cid,
        landed_strength="neutral",
        target_employer="Acme Corp",
        target_role="Inclusive Design Lead",
        factor_1="Yes — formal employer programme verified",
        factor_2="Yes — accessibility-adjacent role",
        factor_3="Yes — community-led recruiting channel",
        factor_4="No",
        factor_5="Conditional yes — employer/role dependent",
        factor_6="No professional advice yet",
        notes="Marker text WXYZ123 for content verification.",
    )
    return cid, sid


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

def test_render_markdown_includes_all_required_sections(candidate_and_session):
    from scripts.generators.disclosure_worksheet import render_markdown
    from scripts.tracker.candidates import get_candidate
    from scripts.tracker.disclosure import get_session
    cid, sid = candidate_and_session
    md = render_markdown(get_session(sid), get_candidate(cid))
    for required in (
        "# BRAINS Resume Skill — Disclosure Decision Worksheet",
        "Matthew Gell",
        "## Boundary statements",
        "## Default position",
        "## Your six-factor answers",
        "## Landed disclosure strength",
        "## Talking points for downstream disclosure",
        "## Recommended next steps",
        "## Boundary statements (restated)",
        "Built by neurodivergent minds, for neurodivergent people.",
        "Disclosure guidance developed with BRAINS Trust safeguarding principles.",
    ):
        assert required in md, f"Markdown missing required section: {required!r}"


def test_render_markdown_substitutes_factors_and_strength(candidate_and_session):
    from scripts.generators.disclosure_worksheet import render_markdown
    from scripts.tracker.candidates import get_candidate
    from scripts.tracker.disclosure import get_session
    cid, sid = candidate_and_session
    md = render_markdown(get_session(sid), get_candidate(cid))
    assert "Yes — formal employer programme verified" in md
    assert "Conditional yes — employer/role dependent" in md
    assert "You landed on: neutral signalling" in md
    assert "Acme Corp" in md
    assert "Inclusive Design Lead" in md


def test_render_markdown_includes_notes_block(candidate_and_session):
    from scripts.generators.disclosure_worksheet import render_markdown
    from scripts.tracker.candidates import get_candidate
    from scripts.tracker.disclosure import get_session
    cid, sid = candidate_and_session
    md = render_markdown(get_session(sid), get_candidate(cid))
    assert "## Notes" in md
    assert "WXYZ123" in md


def test_render_markdown_omits_notes_when_none(isolated):
    from scripts.generators.disclosure_worksheet import render_markdown
    from scripts.tracker.candidates import create_candidate, get_candidate
    from scripts.tracker.disclosure import create_session, get_session
    cid = create_candidate("Sam", "Test", [], None, None)
    sid = create_session(candidate_id=cid, landed_strength="non-disclosure")
    md = render_markdown(get_session(sid), get_candidate(cid))
    assert "## Notes" not in md
    assert "You landed on: non-disclosure" in md


def test_render_markdown_omits_target_lines_when_empty(isolated):
    from scripts.generators.disclosure_worksheet import render_markdown
    from scripts.tracker.candidates import create_candidate, get_candidate
    from scripts.tracker.disclosure import create_session, get_session
    cid = create_candidate("Sam", "Test", [], None, None)
    sid = create_session(candidate_id=cid, landed_strength="undecided")
    md = render_markdown(get_session(sid), get_candidate(cid))
    assert "Target employer:" not in md
    assert "Target role:" not in md


def test_render_markdown_handles_missing_factors(isolated):
    """Factor answers not recorded render as '(not recorded)' rather than blank."""
    from scripts.generators.disclosure_worksheet import render_markdown
    from scripts.tracker.candidates import create_candidate, get_candidate
    from scripts.tracker.disclosure import create_session, get_session
    cid = create_candidate("Sam", "Test", [], None, None)
    sid = create_session(candidate_id=cid, landed_strength="non-disclosure")
    md = render_markdown(get_session(sid), get_candidate(cid))
    assert "(not recorded)" in md


# ---------------------------------------------------------------------------
# PDF rendering
# ---------------------------------------------------------------------------

def test_render_pdf_writes_a_file(candidate_and_session, tmp_path):
    from scripts.generators.disclosure_worksheet import render_pdf
    from scripts.tracker.candidates import get_candidate
    from scripts.tracker.disclosure import get_session
    cid, sid = candidate_and_session
    out = tmp_path / "disclosure.pdf"
    render_pdf(get_session(sid), get_candidate(cid), out)
    assert out.exists() and out.stat().st_size > 0


def test_render_pdf_contains_key_text(candidate_and_session, tmp_path):
    from scripts.generators.disclosure_worksheet import render_pdf
    from scripts.tracker.candidates import get_candidate
    from scripts.tracker.disclosure import get_session
    cid, sid = candidate_and_session
    out = tmp_path / "disclosure.pdf"
    render_pdf(get_session(sid), get_candidate(cid), out)
    with pdfplumber.open(out) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    assert "Disclosure Decision Worksheet" in text
    assert "Matthew Gell" in text
    assert "neutral signalling" in text
    assert "Boundary statements" in text
    # trust footer (verbatim from references/workflows/disclosure.md)
    assert "Disclosure guidance developed with BRAINS Trust safeguarding principles." in text
    # origin phrase (protected, verbatim)
    assert "Built by neurodivergent minds, for neurodivergent people." in text


def test_render_pdf_omits_notes_when_none(isolated, tmp_path):
    from scripts.generators.disclosure_worksheet import render_pdf
    from scripts.tracker.candidates import create_candidate, get_candidate
    from scripts.tracker.disclosure import create_session, get_session
    cid = create_candidate("Sam", "Test", [], None, None)
    sid = create_session(candidate_id=cid, landed_strength="non-disclosure")
    out = tmp_path / "disclosure.pdf"
    render_pdf(get_session(sid), get_candidate(cid), out)
    with pdfplumber.open(out) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    # The "Notes" section header is omitted when no notes were saved.
    # ("not recorded" would still appear in the factor table if all factors blank.)
    assert "\nNotes\n" not in text


# ---------------------------------------------------------------------------
# generate() orchestrator
# ---------------------------------------------------------------------------

def test_generate_writes_both_files_and_persists_uid(candidate_and_session):
    from scripts.generators.disclosure_worksheet import generate
    from scripts.tracker.disclosure import get_session
    _, sid = candidate_and_session
    md_path, pdf_path = generate(sid)
    assert md_path.exists() and pdf_path.exists()
    assert md_path.suffix == ".md"
    assert pdf_path.suffix == ".pdf"

    # uid persisted to the row
    refreshed = get_session(sid)
    assert refreshed.artifact_uid is not None
    assert refreshed.artifact_uid in md_path.name
    assert refreshed.artifact_uid in pdf_path.name


def test_generate_uses_candidate_slug_folder(candidate_and_session):
    from scripts.generators.disclosure_worksheet import generate
    _, sid = candidate_and_session
    md_path, _ = generate(sid)
    assert "Matthew-Gell" in str(md_path)
    assert md_path.name.startswith("disclosure-")


def test_generate_reuses_existing_artifact_uid(candidate_and_session):
    from scripts.generators.disclosure_worksheet import generate
    from scripts.tracker.disclosure import set_artifact_uid, get_session
    _, sid = candidate_and_session
    set_artifact_uid(sid, "preassigned")
    md_path, pdf_path = generate(sid)
    assert "preassigned" in md_path.name
    assert "preassigned" in pdf_path.name
    assert get_session(sid).artifact_uid == "preassigned"


def test_generate_raises_for_missing_session(isolated):
    from scripts.generators.disclosure_worksheet import generate
    with pytest.raises(ValueError, match="session"):
        generate(9999)


def test_generate_respects_explicit_output_root(candidate_and_session, tmp_path):
    from scripts.generators.disclosure_worksheet import generate
    _, sid = candidate_and_session
    custom = tmp_path / "custom-out"
    md_path, pdf_path = generate(sid, output_root=custom)
    assert custom in md_path.parents
    assert custom in pdf_path.parents
