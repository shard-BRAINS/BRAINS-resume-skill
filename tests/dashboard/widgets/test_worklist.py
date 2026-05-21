"""Tests for the worklist widget's pure helper."""
from datetime import datetime, timedelta

import pytest

from scripts.tracker.candidates import create_candidate, set_active_candidate
from scripts.tracker.add import add_jd, add_resume_version, add_application
from scripts.playbooks.runs import start_run
from scripts.dashboard.widgets.worklist import compute_worklist


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_empty_worklist(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    assert compute_worklist(cid) == []


def test_active_run_produces_a_worklist_item(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    start_run(cid, "apply_to_job")
    items = compute_worklist(cid)
    assert any("Apply to a job" in it["text"] for it in items)


def test_stale_application_produces_an_item(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    jd = add_jd("manual", None, "Acme", "Eng", "x", {}, [], [])
    rv = add_resume_version(None, "hybrid", [], tagged_jd_id=jd)
    add_application(jd, rv, None, datetime.now() - timedelta(days=10), "direct")
    items = compute_worklist(cid)
    assert any("Acme" in it["text"] for it in items)


def test_every_item_has_text_and_severity(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    start_run(cid, "build_resume")
    for it in compute_worklist(cid):
        assert it["text"]
        assert it["severity"] in ("high", "medium", "low")
