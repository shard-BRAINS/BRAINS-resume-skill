# tests/test_smoke_drift_end_to_end.py
"""End-to-end smoke for v1.7.0 — import baseline → derivative → drift correctness."""
import json

import pytest

from scripts.tracker.db import open_db


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    monkeypatch.setenv("BRAINS_OUTPUTS_DIR", str(tmp_path / "outputs"))
    from scripts.tracker.profile import write_profile
    from scripts.tracker.models import Profile
    write_profile(Profile(first_name="Matthew", last_name="Gell"))
    return tmp_path


def test_drift_pipeline_end_to_end(monkeypatch, isolated):
    """Mathilda baseline imported → /brains-tailor derivative → drift scores."""
    from scripts.dashboard.workflows import import_ as import_mod
    from scripts.drift import extract_facts, on_artifact_finalised
    from scripts.tracker.add import add_resume_version

    BASELINE_FACTS = {
        "identity": {"name": "Mathilda Gell", "location": "Rochedale, QLD",
                     "email": "m@x", "phone": "0433814874"},
        "experience": [{
            "entry_id": "exp-1", "employer": "Faith Christian Distance Education",
            "title": "Holiday Work", "start_date": "2026-01", "end_date": "2026-01",
            "location": "Brisbane, QLD",
            "key_points": ["Packed enrolment packs."],
        }],
        "education": [{
            "entry_id": "edu-1", "institution": "Redeemer Lutheran College",
            "qualification": "Grade 10", "completion_year": "2028",
            "completion_status": "expected", "honours": [],
        }],
        "skills": ["Customer engagement", "Public speaking", "Team leadership"],
        "certifications": [{"name": "Black Belt Tae Kwon Do",
                            "issuer": None, "year": None}],
        "standalone_achievements": ["Netball MVP 2025"],
        "hobbies": ["Netball", "Archery", "Tae Kwon Do"],
        "languages": [{"language": "English", "proficiency": "native"}],
        "publications": None,
        "portfolio_links": None,
    }
    monkeypatch.setattr(extract_facts, "_call_llm", lambda prompt: BASELINE_FACTS)

    # 1. Import the baseline.
    result = import_mod.run_import(
        source_text="Mathilda's baseline resume text",
        for_candidate="Mathilda Gell",
        confirm_despite_warnings=False,
    )
    assert result["status"] == "imported"
    baseline_uid = result["artifact_uid"]

    # 2. Generate a derivative (simulated workflow handoff).
    derivative_data = {
        "candidate_name": "Mathilda Gell",
        "candidate_contact_line": "Brisbane, QLD  ·  0433814874  ·  m@x",
        "summary": "...",
        "skills": "• Customer engagement\n• Public speaking",  # one skill removed
        "experience": (
            "Holiday Work — Faith Christian Distance Education\n"
            "Brisbane, QLD  ·  January 2026\n"
            "• Packed enrolment packs."
        ),
        "education": (
            "Redeemer Lutheran College — Rochedale, QLD\n"
            "Grade 10  ·  Expected completion 2028"
        ),
    }
    add_resume_version(None, "hybrid", [], artifact_uid="DERIV",
                       parent_uid=baseline_uid, for_candidate="Mathilda Gell")
    on_artifact_finalised("DERIV", derivative_data, kind="resume")

    # 3. Assert drift compute results.
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT vs_parent_score, vs_baseline_score "
            "FROM resume_drift_scores WHERE artifact_uid=?", ("DERIV",),
        ).fetchone()
    finally:
        conn.close()
    vs_parent = json.loads(row[0])
    vs_baseline = json.loads(row[1])

    # Identity: location changed from Rochedale → Brisbane → 1/4 = 25%.
    assert vs_parent["identity"]["pct"] == 25.0
    # Skills: Team leadership removed → 1/3 = ~33%.
    assert vs_parent["skills"]["pct"] == pytest.approx(33.333333, abs=0.01)
    # Hobbies / languages / certifications / standalone_achievements are
    # null in the derivative (workflow doesn't capture them) → skipped.
    for cls in ("hobbies", "languages", "certifications", "standalone_achievements"):
        assert vs_parent[cls] == {"status": "not_captured", "pct": None}
    # Overall renormalised across identity + experience + education + skills.
    assert vs_parent["overall_pct"] is not None
    assert vs_parent["overall_pct"] > 0.0
    # vs_baseline matches vs_parent because parent IS the baseline.
    assert vs_baseline["overall_pct"] == vs_parent["overall_pct"]


def test_promote_baseline_recompute_end_to_end(monkeypatch, isolated):
    """Promote V2 → V3's vs_baseline_score recomputes against V2's facts."""
    from scripts.drift import extract_facts
    from scripts.drift.baseline import promote_baseline
    from scripts.drift.compute import write_snapshot_and_compute_drift
    from scripts.tracker.add import add_resume_version

    facts_a = {
        "identity": {"name": "X", "location": "Q", "email": "x@y", "phone": "0"},
        "experience": [], "education": [], "skills": ["A"],
        "certifications": None, "standalone_achievements": None,
        "hobbies": None, "languages": None, "publications": None,
        "portfolio_links": None,
    }
    facts_b = {**facts_a, "skills": ["A", "B"]}
    facts_c = {**facts_a, "skills": ["A", "B", "C"]}

    add_resume_version(None, "hybrid", [], artifact_uid="A", for_candidate="X")
    write_snapshot_and_compute_drift("A", facts_a)
    add_resume_version(None, "hybrid", [], artifact_uid="B",
                       parent_uid="A", for_candidate="X")
    write_snapshot_and_compute_drift("B", facts_b)
    add_resume_version(None, "hybrid", [], artifact_uid="C",
                       parent_uid="B", for_candidate="X")
    write_snapshot_and_compute_drift("C", facts_c)

    # Before promotion: C's vs_baseline_score is computed against A.
    conn = open_db()
    try:
        before = conn.execute(
            "SELECT vs_baseline_score FROM resume_drift_scores WHERE artifact_uid='C'"
        ).fetchone()
    finally:
        conn.close()
    before_pct = json.loads(before[0])["skills"]["pct"]
    # A→C: skills [A] → [A,B,C] → 2 added of 3 = ~66.7%.
    assert before_pct == pytest.approx(66.666666, abs=0.01)

    # Promote B.
    promote_baseline("B", reason="Real-life change")

    # After: C's vs_baseline_score is against B.
    conn = open_db()
    try:
        after = conn.execute(
            "SELECT vs_baseline_score FROM resume_drift_scores WHERE artifact_uid='C'"
        ).fetchone()
    finally:
        conn.close()
    after_pct = json.loads(after[0])["skills"]["pct"]
    # B→C: skills [A,B] → [A,B,C] → 1 added of 3 = ~33%.
    assert after_pct == pytest.approx(33.333333, abs=0.01)
