"""Tests for scripts/tracker/add.py — the insert-side public API."""
from datetime import datetime
import sqlite3

import pytest

from scripts.tracker.db import open_db
from scripts.tracker.add import (
    add_resume_version, add_jd, add_cover_letter, add_application,
    record_outcome,
)


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


def _seed_resume_and_jd(fresh_db):
    """Helper: seed a resume_version and a jd, return their ids."""
    rv_id = add_resume_version(
        file_path=None, template="chronological", focus_areas=[],
    )
    jd_id = add_jd(
        source="paste", source_ref=None, company="X", role_title="Y",
        raw_text="z", analyzer_findings={},
        focus_areas_required=[], focus_areas_nice=[],
    )
    return rv_id, jd_id


def test_add_cover_letter_returns_id(fresh_db):
    rv_id, jd_id = _seed_resume_and_jd(fresh_db)
    cl_id = add_cover_letter(
        file_path="/tmp/cl.docx",
        resume_version_id=rv_id, jd_id=jd_id,
        template="formal-business",
    )
    assert isinstance(cl_id, int)
    assert cl_id > 0


def test_add_cover_letter_enforces_resume_fk(fresh_db):
    _seed_resume_and_jd(fresh_db)  # create a valid jd_id=1
    with pytest.raises(sqlite3.IntegrityError):
        add_cover_letter(
            file_path=None, resume_version_id=999,  # bad
            jd_id=1, template="formal-business",
        )


def test_add_application_returns_id(fresh_db):
    rv_id, jd_id = _seed_resume_and_jd(fresh_db)
    app_id = add_application(
        jd_id=jd_id, resume_version_id=rv_id, cover_letter_id=None,
        submitted_at=datetime(2026, 5, 13, 14, 30),
        channel="linkedin",
    )
    assert app_id > 0


def test_add_application_persists_all_fields(fresh_db):
    rv_id, jd_id = _seed_resume_and_jd(fresh_db)
    app_id = add_application(
        jd_id=jd_id, resume_version_id=rv_id, cover_letter_id=None,
        submitted_at=datetime(2026, 5, 13, 14, 30),
        channel="agency",
        agency_name="Acme Recruiting",
        recruiter_contact="jane@example.invalid",
        notes="precheck answered",
    )
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT channel, agency_name, recruiter_contact, notes "
            "FROM applications WHERE id=?", (app_id,)
        ).fetchone()
    finally:
        conn.close()
    assert row[0] == "agency"
    assert row[1] == "Acme Recruiting"
    assert row[2] == "jane@example.invalid"
    assert row[3] == "precheck answered"


def test_add_application_enforces_jd_fk(fresh_db):
    rv_id, _jd_id = _seed_resume_and_jd(fresh_db)
    with pytest.raises(sqlite3.IntegrityError):
        add_application(
            jd_id=999, resume_version_id=rv_id, cover_letter_id=None,
            submitted_at=datetime.now(), channel="direct",
        )


def test_record_outcome_returns_id(fresh_db):
    rv_id, jd_id = _seed_resume_and_jd(fresh_db)
    app_id = add_application(
        jd_id=jd_id, resume_version_id=rv_id, cover_letter_id=None,
        submitted_at=datetime.now(), channel="direct",
    )
    oc_id = record_outcome(
        application_id=app_id,
        event_type="callback",
        event_date=datetime(2026, 5, 20),
    )
    assert oc_id > 0


def test_record_outcome_rejects_invalid_event_type(fresh_db):
    rv_id, jd_id = _seed_resume_and_jd(fresh_db)
    app_id = add_application(
        jd_id=jd_id, resume_version_id=rv_id, cover_letter_id=None,
        submitted_at=datetime.now(), channel="direct",
    )
    with pytest.raises(ValueError) as exc_info:
        record_outcome(
            application_id=app_id, event_type="not_a_real_event",
            event_date=datetime.now(),
        )
    assert "not_a_real_event" in str(exc_info.value)


def test_record_outcome_enforces_application_fk(fresh_db):
    with pytest.raises(sqlite3.IntegrityError):
        record_outcome(
            application_id=999, event_type="callback",
            event_date=datetime.now(),
        )


def test_add_application_rejects_invalid_channel(fresh_db):
    rv_id, jd_id = _seed_resume_and_jd(fresh_db)
    with pytest.raises(ValueError) as exc_info:
        add_application(
            jd_id=jd_id, resume_version_id=rv_id, cover_letter_id=None,
            submitted_at=datetime.now(), channel="not_a_real_channel",
        )
    assert "not_a_real_channel" in str(exc_info.value)
