"""Tests for the Home tab's onboarding gate."""
from pathlib import Path

import pytest

APP_PATH = str(Path("scripts/dashboard/app.py").resolve())


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    from scripts.dashboard.data import clear_all_caches
    clear_all_caches()
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_home_module_references_onboarding(isolated):
    """home.py must wire in the onboarding surface."""
    src = Path("scripts/dashboard/tabs/home.py").read_text(encoding="utf-8")
    assert "onboarding" in src


def test_app_loads_with_uncollected_intent_candidate(isolated):
    """A candidate whose intent is unset must not break the Home render."""
    from scripts.tracker.candidates import create_candidate, set_active_candidate
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=20)
    assert not at.exception, f"App raised: {at.exception}"


def test_app_loads_with_collected_intent_candidate(isolated):
    from scripts.tracker.candidates import (
        create_candidate, set_active_candidate, update_candidate_intent,
    )
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    update_candidate_intent(cid, career_stage="mid")
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=20)
    assert not at.exception, f"App raised: {at.exception}"
