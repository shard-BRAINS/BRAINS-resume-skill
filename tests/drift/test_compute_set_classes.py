"""Drift for set-shaped classes (skills, standalone_achievements, hobbies)."""
import pytest

from scripts.drift.compute import compute_class_diff


def test_set_class_unchanged():
    out = compute_class_diff(["A", "B", "C"], ["A", "B", "C"], kind="set")
    assert out == {"added": [], "removed": [], "total": 3, "pct": 0.0}


def test_set_class_one_added():
    out = compute_class_diff(["A", "B"], ["A", "B", "C"], kind="set")
    assert out["added"] == ["C"]
    assert out["removed"] == []
    assert out["total"] == 3
    assert out["pct"] == pytest.approx(33.333333, abs=0.001)


def test_set_class_one_removed():
    out = compute_class_diff(["A", "B", "C"], ["A", "B"], kind="set")
    assert out["added"] == []
    assert out["removed"] == ["C"]
    assert out["total"] == 3  # max(3, 2)
    assert out["pct"] == pytest.approx(33.333333, abs=0.001)


def test_set_class_both_added_and_removed():
    out = compute_class_diff(["A", "B"], ["B", "C"], kind="set")
    assert out["added"] == ["C"]
    assert out["removed"] == ["A"]
    assert out["total"] == 2  # max(2, 2)
    assert out["pct"] == 100.0


def test_set_class_all_removed():
    out = compute_class_diff(["A", "B", "C"], [], kind="set")
    assert out["added"] == []
    assert out["removed"] == ["A", "B", "C"]
    assert out["total"] == 3
    assert out["pct"] == 100.0


def test_set_class_both_empty():
    out = compute_class_diff([], [], kind="set")
    assert out == {"added": [], "removed": [], "total": 0, "pct": 0.0}


def test_set_class_null_left_returns_status_not_captured():
    out = compute_class_diff(None, ["A"], kind="set")
    assert out == {"status": "not_captured", "pct": None}


def test_set_class_null_right_returns_status_not_captured():
    out = compute_class_diff(["A"], None, kind="set")
    assert out == {"status": "not_captured", "pct": None}


def test_set_class_both_null_returns_status_not_captured():
    out = compute_class_diff(None, None, kind="set")
    assert out == {"status": "not_captured", "pct": None}
