"""Smoke test for the deterministic portion of the jd-analyze workflow.

Exercises: jd_analyze runs end-to-end on a fixture, the result carries all
expected fields, and persisting via add_jd works.
"""
from pathlib import Path

from scripts.tracker.add import add_jd
from scripts.tracker.db import open_db
from scripts.validators.jd_analyzer import jd_analyze
from tests.fixtures import jd_analyzer_fixtures as fx


def test_jd_analyze_smoke(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "t.db"))

    # (a) Analyse a mixed JD with focus areas + company + role
    result = jd_analyze(
        jd_text=fx.MIXED_JD,
        focus_areas=["python", "cloud"],
        company="Example Corp",
        role_title="Senior Engineer",
    )

    codes = {f.code for f in result.findings}
    assert "JD_RED_FLAG_SOFT_CULTURE" in codes
    assert "JD_EVIDENCE_OF_FLEX" in codes
    assert "JD_REQ_VS_NICE_PARSING" in codes
    assert "JD_ROLE_FIT_SCORE" in codes
    assert result.role_fit_score is not None

    # (b) Persist to tracker
    jd_id = add_jd(
        source="paste", source_ref=None,
        company="Example Corp", role_title="Senior Engineer",
        raw_text=fx.MIXED_JD,
        analyzer_findings={"finding_count": len(result.findings)},
        focus_areas_required=result.required_list,
        focus_areas_nice=result.nice_list,
    )
    assert jd_id > 0

    conn = open_db()
    try:
        row = conn.execute(
            "SELECT company, role_title FROM jds WHERE id=?", (jd_id,)
        ).fetchone()
    finally:
        conn.close()
    assert row[0] == "Example Corp"
    assert row[1] == "Senior Engineer"
