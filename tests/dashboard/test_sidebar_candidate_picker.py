"""Sidebar candidate picker — wiring + active-candidate persistence."""
import pytest


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_sidebar_module_imports_with_candidate_picker(isolated):
    """Smoke: the rewritten sidebar imports without error."""
    import importlib
    from scripts.dashboard import sidebar
    importlib.reload(sidebar)
    assert hasattr(sidebar, "render")


def test_picker_pre_selects_active_candidate(isolated, monkeypatch):
    """When an active candidate is set, the picker's default index points to it."""
    from scripts.tracker.candidates import create_candidate, set_active_candidate

    a = create_candidate("Matthew", "Gell", [], None, None)
    b = create_candidate("Mathilda", "Gell", [], None, None)
    set_active_candidate(b)

    from scripts.dashboard.sidebar import _resolve_picker_default_index
    from scripts.tracker.candidates import list_candidates
    candidates_in_order = list_candidates()
    idx = _resolve_picker_default_index(candidates_in_order, active_id=b)
    # b is the second candidate created -> index 1 (list_candidates orders by created_at ASC)
    assert candidates_in_order[idx].id == b


def test_picker_default_index_zero_when_no_active(isolated):
    from scripts.dashboard.sidebar import _resolve_picker_default_index
    assert _resolve_picker_default_index([], active_id=None) == 0
