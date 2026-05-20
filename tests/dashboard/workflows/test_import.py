"""/brains-import workflow card — LLM-stubbed end-to-end."""
import pytest


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    monkeypatch.setenv("BRAINS_OUTPUTS_DIR", str(tmp_path / "outputs"))
    from scripts.tracker.candidates import create_candidate, set_active_candidate
    cid = create_candidate(
        first_name="Mathilda", last_name="Gell",
        focus_areas=[], healthy_weekly_rate=None, pacing_notes=None,
    )
    set_active_candidate(cid)
    return tmp_path


VALID_FACTS = {
    "identity": {"name": "Matthew Gell", "location": "Brisbane, QLD",
                 "email": "m@gell.com", "phone": "0400000000"},
    "experience": [], "education": [], "skills": ["Python"],
    "certifications": None, "standalone_achievements": None,
    "hobbies": None, "languages": None, "publications": None,
    "portfolio_links": None,
}


def test_resolve_target_uses_active_candidate(fresh_db):
    from scripts.dashboard.workflows.import_ import _resolve_target
    from scripts.tracker.candidates import get_active_candidate

    active = get_active_candidate()
    path, meta, candidate_id = _resolve_target()
    assert "Mathilda" in path.name
    assert meta.candidate_id == active.id
    assert candidate_id == active.id


def test_resolve_target_raises_with_no_active_candidate(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    monkeypatch.setenv("BRAINS_OUTPUTS_DIR", str(tmp_path / "outputs"))
    from scripts.dashboard.workflows.import_ import _resolve_target
    from scripts.tracker.add import NoActiveCandidateError

    with pytest.raises(NoActiveCandidateError):
        _resolve_target()


def test_commit_writes_row_snapshot_and_drift(monkeypatch, fresh_db):
    """The import commit path persists everything end-to-end."""
    from scripts.dashboard.workflows import import_ as import_mod
    from scripts.drift import extract_facts

    monkeypatch.setattr(extract_facts, "_call_llm", lambda prompt: VALID_FACTS)

    from scripts.tracker.candidates import get_active_candidate
    active = get_active_candidate()

    result = import_mod.run_import(
        source_text="Mathilda's resume text...",
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
            "SELECT artifact_uid, candidate_id, is_baseline "
            "FROM resume_versions WHERE artifact_uid=?",
            (result["artifact_uid"],),
        ).fetchone()
        snap = conn.execute(
            "SELECT COUNT(*) FROM resume_fact_snapshots WHERE artifact_uid=?",
            (result["artifact_uid"],),
        ).fetchone()[0]
    finally:
        conn.close()
    assert rv[1] == active.id  # linked to the active candidate
    assert rv[2] == 1  # auto-baseline (first row for Mathilda)
    assert snap == 1


def test_commit_blocked_by_implausibility_unless_confirmed(monkeypatch, fresh_db):
    from scripts.dashboard.workflows import import_ as import_mod
    from scripts.drift import extract_facts

    bad = {**VALID_FACTS, "identity": {**VALID_FACTS["identity"], "name": "John Doe"}}
    monkeypatch.setattr(extract_facts, "_call_llm", lambda prompt: bad)

    result = import_mod.run_import(
        source_text="text",
        confirm_despite_warnings=False,
    )
    assert result["status"] == "needs_confirmation"
    assert any("placeholder" in w.lower() for w in result["warnings"])
    assert result["artifact_uid"] is None

    # User confirms; import proceeds.
    result2 = import_mod.run_import(
        source_text="text",
        confirm_despite_warnings=True,
    )
    assert result2["status"] == "imported"
