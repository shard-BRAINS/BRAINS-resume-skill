"""Per-class drift for the six list-of-object classes."""
import pytest

from scripts.drift.compute import compute_class_diff


EXP_A = [
    {"entry_id": "exp-1", "employer": "Acme", "title": "Engineer",
     "start_date": "2024-01", "end_date": "2025-12",
     "location": "Brisbane, QLD", "key_points": ["Did X"]},
]
EXP_B = [
    {"entry_id": "exp-1", "employer": "Acme", "title": "Engineer II",
     "start_date": "2024-01", "end_date": "2025-12",
     "location": "Brisbane, QLD", "key_points": ["Did X"]},
]
EXP_C_NEW_ENTRY = [
    {"entry_id": "exp-1", "employer": "Acme", "title": "Engineer",
     "start_date": "2024-01", "end_date": "2025-12",
     "location": "Brisbane, QLD", "key_points": ["Did X"]},
    {"entry_id": "exp-2", "employer": "Beta", "title": "Senior",
     "start_date": "2026-01", "end_date": "present",
     "location": "Brisbane, QLD", "key_points": ["Did Y"]},
]


def test_experience_unchanged():
    out = compute_class_diff(EXP_A, EXP_A, kind="experience")
    assert out["entries_added"] == 0
    assert out["entries_removed"] == 0
    assert out["entries_with_field_changes"] == 0
    assert out["entries_total"] == 1
    assert out["pct"] == 0.0
    assert out["field_changes"] == []


def test_experience_title_field_change():
    out = compute_class_diff(EXP_A, EXP_B, kind="experience")
    assert out["entries_with_field_changes"] == 1
    assert any(fc["field"] == "title" for fc in out["field_changes"])
    assert out["entries_total"] == 1
    assert out["pct"] == 100.0


def test_experience_entry_added():
    out = compute_class_diff(EXP_A, EXP_C_NEW_ENTRY, kind="experience")
    assert out["entries_added"] == 1
    assert out["entries_removed"] == 0
    assert out["entries_total"] == 2
    assert out["pct"] == 50.0


def test_experience_natural_key_matches_across_reorder():
    """Same entries in different order — should match via (employer, start_date)."""
    out = compute_class_diff(EXP_C_NEW_ENTRY, list(reversed(EXP_C_NEW_ENTRY)), kind="experience")
    assert out["pct"] == 0.0


def test_experience_fuzzy_fallback_matches_renamed_employer():
    """Employer renamed slightly — fuzzy match prevents 'added + removed'."""
    left = [{"entry_id": "exp-1", "employer": "Acme Corporation",
             "title": "Engineer", "start_date": "2024-01",
             "end_date": "2025-12", "location": "Brisbane, QLD",
             "key_points": []}]
    right = [{"entry_id": "exp-1", "employer": "Acme Corp.",
              "title": "Engineer", "start_date": "2024-01",
              "end_date": "2025-12", "location": "Brisbane, QLD",
              "key_points": []}]
    out = compute_class_diff(left, right, kind="experience")
    # Natural key (employer + start_date) doesn't match exactly; fuzzy
    # fallback should treat them as the same entry with employer changed.
    assert out["entries_added"] == 0
    assert out["entries_removed"] == 0
    assert out["entries_with_field_changes"] == 1
    assert any(fc["field"] == "employer" for fc in out["field_changes"])


def test_education_natural_key_institution_qualification():
    left = [{"entry_id": "edu-1", "institution": "X High",
             "qualification": "Year 12", "completion_year": "2027",
             "completion_status": "expected", "honours": []}]
    right = [{"entry_id": "edu-1", "institution": "X High",
              "qualification": "Year 12", "completion_year": "2027",
              "completion_status": "completed", "honours": []}]
    out = compute_class_diff(left, right, kind="education")
    assert out["entries_with_field_changes"] == 1
    assert any(fc["field"] == "completion_status" for fc in out["field_changes"])
    assert out["pct"] == 100.0


def test_certifications_natural_key_by_name():
    left = [{"name": "AWS SAA", "issuer": "Amazon", "year": "2023"}]
    right = [{"name": "AWS SAA", "issuer": "Amazon", "year": "2024"}]
    out = compute_class_diff(left, right, kind="certifications")
    assert any(fc["field"] == "year" for fc in out["field_changes"])
    assert out["pct"] == 100.0


def test_languages_proficiency_change():
    left = [{"language": "Spanish", "proficiency": "basic"}]
    right = [{"language": "Spanish", "proficiency": "conversational"}]
    out = compute_class_diff(left, right, kind="languages")
    assert any(fc["field"] == "proficiency" for fc in out["field_changes"])
    assert out["pct"] == 100.0


def test_languages_added_entry():
    left = [{"language": "English", "proficiency": "native"}]
    right = [{"language": "English", "proficiency": "native"},
             {"language": "Spanish", "proficiency": "basic"}]
    out = compute_class_diff(left, right, kind="languages")
    assert out["entries_added"] == 1
    assert out["pct"] == 50.0


def test_publications_title_year_natural_key():
    left = [{"title": "A study of X", "venue": "Journal Y",
             "year": "2024", "authors": ["A"], "url": None}]
    right = [{"title": "A study of X", "venue": "Journal Y",
              "year": "2024", "authors": ["A", "B"], "url": None}]
    out = compute_class_diff(left, right, kind="publications")
    assert any(fc["field"] == "authors" for fc in out["field_changes"])
    assert out["pct"] == 100.0


def test_portfolio_links_url_canonicalised():
    """Same URL with/without trailing slash, protocol prefix, case differences match."""
    left = [{"label": "GitHub", "url": "https://github.com/Mathilda/"}]
    right = [{"label": "GitHub profile", "url": "github.com/mathilda"}]
    out = compute_class_diff(left, right, kind="portfolio_links")
    # URL canonicalises to same; label is the field change.
    assert out["entries_added"] == 0
    assert out["entries_removed"] == 0
    assert any(fc["field"] == "label" for fc in out["field_changes"])


def test_null_class_returns_not_captured():
    out = compute_class_diff(None, EXP_A, kind="experience")
    assert out == {"status": "not_captured", "pct": None}


def test_empty_vs_populated_is_full_drift():
    """[] vs populated counts as 100% drift (everything 'added')."""
    out = compute_class_diff([], EXP_A, kind="experience")
    assert out["entries_added"] == 1
    assert out["pct"] == 100.0
