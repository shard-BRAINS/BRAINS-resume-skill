"""Headline-changes formatter — priority ordering + ≤5 cap."""
import pytest

from scripts.drift.formatters import format_headline_changes


def test_empty_score_returns_empty_list():
    score = {cls: {"status": "not_captured", "pct": None}
             for cls in ("identity", "experience", "education", "skills",
                         "certifications", "standalone_achievements", "hobbies",
                         "languages", "publications", "portfolio_links")}
    score["overall_pct"] = 0.0
    assert format_headline_changes(score) == []


def test_identity_change_appears_first():
    score = {
        "identity": {"fields_changed": ["location"], "fields_total": 4, "pct": 25.0},
        "experience": {"entries_added": 0, "entries_removed": 0,
                       "entries_with_field_changes": 0, "field_changes": [],
                       "entries_total": 1, "pct": 0.0},
        "education": {"status": "not_captured", "pct": None},
        "skills": {"added": [], "removed": [], "total": 3, "pct": 0.0},
        "certifications": {"status": "not_captured", "pct": None},
        "standalone_achievements": {"status": "not_captured", "pct": None},
        "hobbies": {"status": "not_captured", "pct": None},
        "languages": {"status": "not_captured", "pct": None},
        "publications": {"status": "not_captured", "pct": None},
        "portfolio_links": {"status": "not_captured", "pct": None},
        "overall_pct": 5.0,
    }
    out = format_headline_changes(score)
    assert len(out) == 1
    assert "location" in out[0].lower()


def test_priority_order_identity_then_experience_field_then_added_removed():
    score = {
        "identity": {"fields_changed": ["location"], "fields_total": 4, "pct": 25.0},
        "experience": {"entries_added": 1, "entries_removed": 0,
                       "entries_with_field_changes": 1,
                       "field_changes": [{"entry_id": "exp-1", "field": "title",
                                          "from": "A", "to": "B"}],
                       "entries_total": 2, "pct": 100.0},
        "education": {"status": "not_captured", "pct": None},
        "skills": {"added": ["X"], "removed": [], "total": 4, "pct": 25.0},
        "certifications": {"status": "not_captured", "pct": None},
        "standalone_achievements": {"status": "not_captured", "pct": None},
        "hobbies": {"status": "not_captured", "pct": None},
        "languages": {"status": "not_captured", "pct": None},
        "publications": {"status": "not_captured", "pct": None},
        "portfolio_links": {"status": "not_captured", "pct": None},
        "overall_pct": 30.0,
    }
    out = format_headline_changes(score)
    # Priority: identity → experience field changes → experience entries added → skills added.
    assert out[0].lower().startswith(("identity", "location"))
    assert "title" in out[1].lower() or "experience" in out[1].lower()


def test_capped_at_5():
    """Snapshot with way more than 5 bullets — output capped."""
    score = {
        "identity": {"fields_changed": ["name", "location", "email", "phone"],
                     "fields_total": 4, "pct": 100.0},
        "experience": {"entries_added": 3, "entries_removed": 2,
                       "entries_with_field_changes": 2,
                       "field_changes": [
                           {"entry_id": f"exp-{i}", "field": "title",
                            "from": "A", "to": "B"} for i in range(5)
                       ],
                       "entries_total": 5, "pct": 100.0},
        "education": {"entries_added": 1, "entries_removed": 0,
                      "entries_with_field_changes": 0, "field_changes": [],
                      "entries_total": 1, "pct": 100.0},
        "skills": {"added": ["X", "Y", "Z"], "removed": ["A"],
                   "total": 10, "pct": 40.0},
        "certifications": {"status": "not_captured", "pct": None},
        "standalone_achievements": {"status": "not_captured", "pct": None},
        "hobbies": {"status": "not_captured", "pct": None},
        "languages": {"status": "not_captured", "pct": None},
        "publications": {"status": "not_captured", "pct": None},
        "portfolio_links": {"status": "not_captured", "pct": None},
        "overall_pct": 90.0,
    }
    out = format_headline_changes(score)
    assert len(out) == 5
