"""Tests for scripts/tracker/add.py — the insert-side public API."""
from datetime import datetime

import pytest

from scripts.tracker.db import open_db
from scripts.tracker.add import add_resume_version, add_jd


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    """Each test gets an isolated empty db."""
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    return tmp_path / "test.db"


def test_add_resume_version_returns_id(fresh_db):
    id_ = add_resume_version(
        file_path="/tmp/r.docx",
        template="hybrid",
        focus_areas=["platform", "observability"],
    )
    assert isinstance(id_, int)
    assert id_ > 0


def test_add_resume_version_persists_to_db(fresh_db):
    id_ = add_resume_version(
        file_path="/tmp/r.docx", template="chronological",
        focus_areas=["x"],
    )
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT file_path, template, focus_areas FROM resume_versions WHERE id=?",
            (id_,),
        ).fetchone()
    finally:
        conn.close()
    assert row[0] == "/tmp/r.docx"
    assert row[1] == "chronological"
    # focus_areas stored as JSON
    import json
    assert json.loads(row[2]) == ["x"]


def test_add_resume_version_accepts_null_file_path(fresh_db):
    id_ = add_resume_version(
        file_path=None, template="executive", focus_areas=[],
    )
    assert id_ > 0


def test_add_resume_version_accepts_parent_id(fresh_db):
    parent = add_resume_version(
        file_path=None, template="chronological", focus_areas=[],
    )
    child = add_resume_version(
        file_path=None, template="chronological", focus_areas=[],
        parent_id=parent,
    )
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT parent_id FROM resume_versions WHERE id=?", (child,)
        ).fetchone()
    finally:
        conn.close()
    assert row[0] == parent


def test_add_jd_returns_id(fresh_db):
    id_ = add_jd(
        source="paste", source_ref=None,
        company="Example Corp", role_title="Senior Engineer",
        raw_text="JD body text",
        analyzer_findings={"red_flags": 2, "score": 75},
        focus_areas_required=["python", "distributed systems"],
        focus_areas_nice=["go"],
    )
    assert isinstance(id_, int)
    assert id_ > 0


def test_add_jd_persists_findings_as_json(fresh_db):
    id_ = add_jd(
        source="paste", source_ref=None,
        company="X", role_title="Y", raw_text="z",
        analyzer_findings={"key": "value"},
        focus_areas_required=[], focus_areas_nice=[],
    )
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT analyzer_findings FROM jds WHERE id=?", (id_,)
        ).fetchone()
    finally:
        conn.close()
    import json
    assert json.loads(row[0]) == {"key": "value"}


def test_add_jd_creates_created_at_timestamp(fresh_db):
    id_ = add_jd(
        source="paste", source_ref=None,
        company="X", role_title="Y", raw_text="z",
        analyzer_findings={}, focus_areas_required=[], focus_areas_nice=[],
    )
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT created_at FROM jds WHERE id=?", (id_,)
        ).fetchone()
    finally:
        conn.close()
    # ISO-8601 with Z suffix
    assert row[0].endswith("Z")
    assert "T" in row[0]
