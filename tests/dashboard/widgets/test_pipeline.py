"""Tests for the pipeline widget's pure helper."""
from datetime import datetime

import pytest

from scripts.tracker.candidates import create_candidate, set_active_candidate
from scripts.tracker.add import (
    add_jd, add_resume_version, add_cover_letter, add_application,
)
from scripts.dashboard.widgets.pipeline import classify_pipeline, PIPELINE_STAGES


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_stages_constant():
    assert PIPELINE_STAGES == ("Lead", "Tailoring", "Docs ready", "Submitted", "Outcome")


def test_empty_pipeline_has_all_stages(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    result = classify_pipeline(cid)
    assert set(result.keys()) == set(PIPELINE_STAGES)
    assert all(v == [] for v in result.values())


def test_jd_only_is_a_lead(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    add_jd("manual", None, "Coles", "Retail", "x", {}, [], [])
    assert [c["company"] for c in classify_pipeline(cid)["Lead"]] == ["Coles"]


def test_jd_with_resume_is_tailoring(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    jd = add_jd("manual", None, "Big W", "Sales", "x", {}, [], [])
    add_resume_version(None, "hybrid", [], tagged_jd_id=jd)
    assert [c["company"] for c in classify_pipeline(cid)["Tailoring"]] == ["Big W"]


def test_application_is_submitted(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    jd = add_jd("manual", None, "Kmart", "Floor", "x", {}, [], [])
    rv = add_resume_version(None, "hybrid", [], tagged_jd_id=jd)
    add_application(jd, rv, None, datetime(2026, 2, 1), "direct")
    assert [c["company"] for c in classify_pipeline(cid)["Submitted"]] == ["Kmart"]
