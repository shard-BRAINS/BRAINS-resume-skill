"""Tests for the widget catalog and layout resolution."""
import pytest

from scripts.dashboard.widgets.catalog import (
    Widget, WIDGET_CATALOG, get_widget, resolve_layout,
)


def test_catalog_has_expected_widgets():
    keys = {w.key for w in WIDGET_CATALOG}
    assert keys == {
        "in_progress_runs",
        "playbook_apply", "playbook_build", "playbook_improve",
        "playbook_linkedin", "playbook_career_change",
        "worklist", "pipeline_mini",
        "tile_pacing", "tile_drift", "tile_library_counts",
        "quick_launch", "tile_recent_outcomes",
    }


def test_every_widget_has_valid_fields():
    for w in WIDGET_CATALOG:
        assert w.zone in ("upper", "lower")
        assert callable(w.render)
        assert w.label


def test_recent_outcomes_is_off_by_default():
    assert get_widget("tile_recent_outcomes").default_enabled is False


def test_playbook_widgets_default_on():
    assert get_widget("playbook_apply").default_enabled is True


def test_get_widget_unknown_raises():
    with pytest.raises(KeyError):
        get_widget("nope")


def test_resolve_layout_empty_returns_full_catalog_defaults():
    resolved = resolve_layout([])
    assert len(resolved) == len(WIDGET_CATALOG)
    by_key = {w.key: enabled for w, enabled in resolved}
    assert by_key["playbook_apply"] is True
    assert by_key["tile_recent_outcomes"] is False


def test_resolve_layout_honours_saved_order_and_enabled():
    resolved = resolve_layout([("worklist", False), ("tile_drift", True)])
    assert resolved[0][0].key == "worklist"
    assert resolved[0][1] is False
    assert resolved[1][0].key == "tile_drift"
    # widgets absent from the saved layout are appended with their defaults
    assert len(resolved) == len(WIDGET_CATALOG)


def test_resolve_layout_drops_unknown_keys():
    resolved = resolve_layout([("removed_widget", True), ("worklist", True)])
    assert all(w.key != "removed_widget" for w, _ in resolved)
    assert resolved[0][0].key == "worklist"
