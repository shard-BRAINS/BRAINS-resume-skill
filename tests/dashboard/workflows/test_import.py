"""/brains-import workflow card — LLM-stubbed end-to-end."""
import pytest


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    monkeypatch.setenv("BRAINS_OUTPUTS_DIR", str(tmp_path / "outputs"))
    from scripts.tracker.profile import write_profile
    from scripts.tracker.models import Profile
    write_profile(Profile(first_name="Matthew", last_name="Gell"))
    return tmp_path


VALID_FACTS = {
    "identity": {"name": "Matthew Gell", "location": "Brisbane, QLD",
                 "email": "m@gell.com", "phone": "0400000000"},
    "experience": [], "education": [], "skills": ["Python"],
    "certifications": None, "standalone_achievements": None,
    "hobbies": None, "languages": None, "publications": None,
    "portfolio_links": None,
}


def test_resolve_target_for_named_candidate(fresh_db):
    from scripts.dashboard.workflows.import_ import _resolve_target

    path, meta, for_candidate = _resolve_target(for_candidate="Mathilda Gell")
    assert "Mathilda" in path.name
    assert meta.for_candidate == "Mathilda Gell"
    assert for_candidate == "Mathilda Gell"


def test_resolve_target_falls_back_to_profile(fresh_db):
    from scripts.dashboard.workflows.import_ import _resolve_target

    path, meta, for_candidate = _resolve_target(for_candidate="")
    assert "Matthew" in path.name
    assert meta.for_candidate is None
    assert for_candidate is None


def test_commit_writes_row_snapshot_and_drift(monkeypatch, fresh_db):
    """The import commit path persists everything end-to-end."""
    from scripts.dashboard.workflows import import_ as import_mod
    from scripts.drift import extract_facts

    monkeypatch.setattr(extract_facts, "_call_llm", lambda prompt: VALID_FACTS)

    result = import_mod.run_import(
        source_text="Mathilda's resume text...",
        for_candidate="Mathilda Gell",
        confirm_despite_warnings=False,
    )
    assert result["status"] == "imported"
    assert result["artifact_uid"] is not None
    assert result["facts"]["identity"]["name"] == "Matthew Gell"  # from VALID_FACTS

    # Confirm DB rows.
    from scripts.tracker.db import open_db
    conn = open_db()
    try:
        rv = conn.execute(
            "SELECT artifact_uid, for_candidate, is_baseline "
            "FROM resume_versions WHERE artifact_uid=?",
            (result["artifact_uid"],),
        ).fetchone()
        snap = conn.execute(
            "SELECT COUNT(*) FROM resume_fact_snapshots WHERE artifact_uid=?",
            (result["artifact_uid"],),
        ).fetchone()[0]
    finally:
        conn.close()
    assert rv[1] == "Mathilda Gell"
    assert rv[2] == 1  # auto-baseline (first row for Mathilda)
    assert snap == 1


def test_commit_blocked_by_implausibility_unless_confirmed(monkeypatch, fresh_db):
    from scripts.dashboard.workflows import import_ as import_mod
    from scripts.drift import extract_facts

    bad = {**VALID_FACTS, "identity": {**VALID_FACTS["identity"], "name": "John Doe"}}
    monkeypatch.setattr(extract_facts, "_call_llm", lambda prompt: bad)

    result = import_mod.run_import(
        source_text="text",
        for_candidate="Mathilda Gell",
        confirm_despite_warnings=False,
    )
    assert result["status"] == "needs_confirmation"
    assert any("placeholder" in w.lower() for w in result["warnings"])
    assert result["artifact_uid"] is None

    # User confirms; import proceeds.
    result2 = import_mod.run_import(
        source_text="text",
        for_candidate="Mathilda Gell",
        confirm_despite_warnings=True,
    )
    assert result2["status"] == "imported"
