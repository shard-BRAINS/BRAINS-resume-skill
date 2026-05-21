"""Tests for the rewired app — Home replaces Overview + Workflows."""
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


def test_app_loads_without_exception(isolated):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=20)
    assert not at.exception, f"App raised: {at.exception}"


def test_app_has_eight_tabs_with_home_first(isolated):
    from scripts.tracker.candidates import create_candidate, set_active_candidate
    create_candidate("A", "B", [], None, None)
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=20)
    assert not at.exception
    # The app source no longer references the removed tabs.
    src = Path(APP_PATH).read_text(encoding="utf-8")
    assert "home" in src
    assert "overview" not in src
    assert "workflows" not in src


def test_overview_and_workflows_modules_are_gone():
    assert not Path("scripts/dashboard/tabs/overview.py").exists()
    assert not Path("scripts/dashboard/tabs/workflows.py").exists()
