"""Tests for playbook completion predicates."""
from datetime import datetime

import pytest

from scripts.tracker.db import open_db
from scripts.tracker.add import (
    add_jd, add_resume_version, add_cover_letter, add_application,
)
from scripts.tracker.candidates import create_candidate, set_active_candidate
from scripts.playbooks.models import PlaybookRun
from scripts.playbooks import predicates as P


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def _run(candidate_id, jd_id=None, created_at="2026-01-01T00:00:00Z"):
    return PlaybookRun(
        id=1, candidate_id=candidate_id, playbook_key="apply_to_job",
        jd_id=jd_id, current_step=0, status="active",
        created_at=created_at, updated_at=created_at, completed_at=None,
    )


def test_resume_tagged_to_jd_false_when_none(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    jd = add_jd("manual", None, "Acme", "Eng", "x", {}, [], [])
    conn = open_db()
    try:
        assert P.resume_tagged_to_jd(conn, _run(cid, jd)) is False
    finally:
        conn.close()


def test_resume_tagged_to_jd_true_when_present(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    jd = add_jd("manual", None, "Acme", "Eng", "x", {}, [], [])
    add_resume_version(None, "hybrid", [], tagged_jd_id=jd)
    conn = open_db()
    try:
        assert P.resume_tagged_to_jd(conn, _run(cid, jd)) is True
    finally:
        conn.close()


def test_resume_tagged_to_jd_false_when_jd_id_none(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    conn = open_db()
    try:
        assert P.resume_tagged_to_jd(conn, _run(cid, None)) is False
    finally:
        conn.close()


def test_cover_letter_for_jd(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    jd = add_jd("manual", None, "Acme", "Eng", "x", {}, [], [])
    rv = add_resume_version(None, "hybrid", [], tagged_jd_id=jd)
    conn = open_db()
    try:
        assert P.cover_letter_for_jd(conn, _run(cid, jd)) is False
    finally:
        conn.close()
    add_cover_letter(None, rv, jd, "standard")
    conn = open_db()
    try:
        assert P.cover_letter_for_jd(conn, _run(cid, jd)) is True
    finally:
        conn.close()


def test_application_for_jd(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    jd = add_jd("manual", None, "Acme", "Eng", "x", {}, [], [])
    rv = add_resume_version(None, "hybrid", [], tagged_jd_id=jd)
    conn = open_db()
    try:
        assert P.application_for_jd(conn, _run(cid, jd)) is False
    finally:
        conn.close()
    add_application(jd, rv, None, datetime(2026, 2, 1), "direct")
    conn = open_db()
    try:
        assert P.application_for_jd(conn, _run(cid, jd)) is True
    finally:
        conn.close()


def test_resume_created_after_run(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    # A resume created BEFORE the run start time must not count.
    add_resume_version(None, "hybrid", [])
    future_run = _run(cid, created_at="2099-01-01T00:00:00Z")
    past_run = _run(cid, created_at="2000-01-01T00:00:00Z")
    conn = open_db()
    try:
        assert P.resume_created_after_run(conn, future_run) is False
        assert P.resume_created_after_run(conn, past_run) is True
    finally:
        conn.close()
