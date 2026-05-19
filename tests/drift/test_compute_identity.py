import pytest

from scripts.drift.compute import compute_class_diff


IDENTITY_A = {"name": "Mathilda Gell", "location": "Rochedale, QLD",
              "email": "m@x.com", "phone": "0433814874"}
IDENTITY_B = {"name": "Mathilda Gell", "location": "Brisbane, QLD",
              "email": "m@x.com", "phone": "0433814874"}


def test_identity_unchanged():
    out = compute_class_diff(IDENTITY_A, dict(IDENTITY_A), kind="identity")
    assert out == {"fields_changed": [], "fields_total": 4, "pct": 0.0}


def test_identity_one_field_changed():
    out = compute_class_diff(IDENTITY_A, IDENTITY_B, kind="identity")
    assert out["fields_changed"] == ["location"]
    assert out["fields_total"] == 4
    assert out["pct"] == 25.0


def test_identity_null_field_counts_when_other_side_has_value():
    left = dict(IDENTITY_A)
    right = dict(IDENTITY_A)
    right["phone"] = None
    out = compute_class_diff(left, right, kind="identity")
    assert out["fields_changed"] == ["phone"]
    assert out["pct"] == 25.0


def test_identity_both_null_on_field_is_not_a_change():
    left = dict(IDENTITY_A); left["phone"] = None
    right = dict(IDENTITY_A); right["phone"] = None
    out = compute_class_diff(left, right, kind="identity")
    assert out["fields_changed"] == []
    assert out["pct"] == 0.0


def test_identity_null_object_returns_not_captured():
    out = compute_class_diff(None, IDENTITY_A, kind="identity")
    assert out == {"status": "not_captured", "pct": None}
