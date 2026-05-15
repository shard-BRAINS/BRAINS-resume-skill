"""AppTest happy-path: the Overview tab renders without exceptions.

Uses streamlit.testing.v1.AppTest to drive a synthetic Streamlit session.
Empty tracker db -> the app should render with "No applications" / idle-state
callouts rather than crashing.
"""
from pathlib import Path

import pytest

APP_PATH = Path(__file__).parent.parent.parent / "scripts" / "dashboard" / "app.py"


@pytest.fixture
def empty_tracker(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "p.json"))
    return tmp_path


def test_app_loads_overview_tab_with_empty_db(empty_tracker):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=10)
    # App should render without exceptions
    assert not at.exception, f"App raised: {at.exception}"


def test_app_renders_title(empty_tracker):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=10)
    # Find the title element
    titles = [t.value for t in at.title]
    assert "BRAINS Resume Dashboard" in titles
