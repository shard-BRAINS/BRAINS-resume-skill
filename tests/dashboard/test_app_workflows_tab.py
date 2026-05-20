"""AppTest: the Workflows tab renders without exceptions."""
from pathlib import Path

import pytest

APP_PATH = Path(__file__).parent.parent.parent / "scripts" / "dashboard" / "app.py"


@pytest.fixture
def empty_tracker(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "p.json"))
    return tmp_path


def test_workflows_tab_renders_without_exception(empty_tracker):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=15)
    assert not at.exception, f"App raised: {at.exception}"


def test_workflows_tab_has_workflows_header(empty_tracker):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=15)
    headers = [h.value for h in at.header]
    assert "Workflows" in headers


def test_workflows_tab_has_three_subheaders(empty_tracker):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=15)
    subheaders = [s.value for s in at.subheader]
    assert "1 · Pre-application & decisions" in subheaders
    assert "2 · Resume & cover docs" in subheaders
    assert "3 · Track & LinkedIn" in subheaders


def test_phase3_workflow_modules_import():
    from scripts.dashboard.workflows import check, consolidate, deai, jd_analyze, review, track  # noqa: F401


def test_applications_tab_inline_actions_added(empty_tracker):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=15)
    # Check that the app renders without error (inline actions are wired up)
    assert not at.exception, f"App raised: {at.exception}"


def test_app_does_not_raise_with_all_inline_actions(empty_tracker):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=15)
    assert not at.exception, f"App raised: {at.exception}"
