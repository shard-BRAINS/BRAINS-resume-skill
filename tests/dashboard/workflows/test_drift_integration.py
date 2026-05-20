"""End-to-end: on_artifact_finalised persists snapshot + drift after a render."""
import pytest

from scripts.tracker.add import add_resume_version
from scripts.tracker.db import open_db


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    return tmp_path


SAMPLE_DATA = {
    "candidate_name": "Mathilda Gell",
    "candidate_contact_line": "Rochedale, QLD  ·  0433  ·  m@x.com",
    "summary": "...",
    "skills": "• A\n• B",
    "experience": "T — E\nB · 2024-01\n• X",
    "education": "I — L\nGrade",
}


def test_on_artifact_finalised_resume_writes_snapshot(fresh_db):
    from scripts.drift import on_artifact_finalised

    add_resume_version(None, "hybrid", [], artifact_uid="ABC",
                       for_candidate="Mathilda Gell")
    on_artifact_finalised("ABC", SAMPLE_DATA, kind="resume")

    conn = open_db()
    try:
        n = conn.execute(
            "SELECT COUNT(*) FROM resume_fact_snapshots WHERE artifact_uid=?",
            ("ABC",),
        ).fetchone()[0]
    finally:
        conn.close()
    assert n == 1


def test_on_artifact_finalised_cover_letter_no_snapshot(fresh_db):
    """Cover letters are out of scope for v1 — no snapshot written."""
    from scripts.drift import on_artifact_finalised

    add_resume_version(None, "hybrid", [], artifact_uid="CL", for_candidate="X")
    on_artifact_finalised("CL", SAMPLE_DATA, kind="cover-letter")

    conn = open_db()
    try:
        n = conn.execute(
            "SELECT COUNT(*) FROM resume_fact_snapshots WHERE artifact_uid=?",
            ("CL",),
        ).fetchone()[0]
    finally:
        conn.close()
    assert n == 0
