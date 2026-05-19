"""End-to-end snapshot diff + overall_pct with renormalisation."""
import pytest

from scripts.drift.compute import compute_drift_score


BASELINE = {
    "identity": {"name": "Mathilda Gell", "location": "Rochedale, QLD",
                 "email": "m@x.com", "phone": "0433"},
    "experience": [
        {"entry_id": "exp-1", "employer": "Acme",
         "title": "Engineer", "start_date": "2024-01",
         "end_date": "2025-12", "location": "Brisbane, QLD",
         "key_points": ["Did X"]}
    ],
    "education": [
        {"entry_id": "edu-1", "institution": "X High",
         "qualification": "Year 12", "completion_year": "2027",
         "completion_status": "expected", "honours": []}
    ],
    "skills": ["A", "B", "C"],
    "certifications": [{"name": "AWS SAA", "issuer": "Amazon", "year": "2023"}],
    "standalone_achievements": ["Award 1"],
    "hobbies": ["Netball"],
    "languages": [{"language": "English", "proficiency": "native"}],
    "publications": [],
    "portfolio_links": [{"label": "GitHub", "url": "github.com/x"}],
}


def test_identical_snapshots_overall_zero():
    out = compute_drift_score(BASELINE, BASELINE)
    assert out["overall_pct"] == 0.0


def test_identity_only_change_uses_identity_weight():
    """Only identity changes (location). Weight 0.20 means overall = 0.20 * 25% = 5.0%."""
    right = {**BASELINE, "identity": {**BASELINE["identity"], "location": "Brisbane, QLD"}}
    out = compute_drift_score(BASELINE, right)
    # identity pct = 25% (1 of 4 fields), weight 0.20 — but all 10 classes are
    # populated on both sides, so overall = 0.20 * 25 = 5.0 (no renormalisation).
    assert out["identity"]["pct"] == 25.0
    assert out["overall_pct"] == pytest.approx(5.0, abs=0.01)


def test_null_class_skipped_and_weights_renormalise():
    """Right side has null for 6 classes — overall_pct should renormalise across
    only the 4 classes both sides cover (identity, experience, education, skills)."""
    right = {
        "identity": BASELINE["identity"],
        "experience": BASELINE["experience"],
        "education": BASELINE["education"],
        "skills": BASELINE["skills"],
        "certifications": None,
        "standalone_achievements": None,
        "hobbies": None,
        "languages": None,
        "publications": None,
        "portfolio_links": None,
    }
    out = compute_drift_score(BASELINE, right)
    # All 4 classes are identical → overall = 0.
    assert out["overall_pct"] == 0.0
    # And the 6 null classes have status 'not_captured'.
    for cls in ("certifications", "standalone_achievements", "hobbies",
                "languages", "publications", "portfolio_links"):
        assert out[cls] == {"status": "not_captured", "pct": None}


def test_null_class_with_changes_in_other_classes():
    """Identity changes 25%, all 6 non-core classes null. Renormalised weights:
    identity 0.20 / (0.20+0.25+0.12+0.08) = 0.3077.
    overall_pct = 0.3077 * 25 = ~7.69."""
    right = {
        "identity": {**BASELINE["identity"], "location": "X"},
        "experience": BASELINE["experience"],
        "education": BASELINE["education"],
        "skills": BASELINE["skills"],
        "certifications": None,
        "standalone_achievements": None,
        "hobbies": None,
        "languages": None,
        "publications": None,
        "portfolio_links": None,
    }
    out = compute_drift_score(BASELINE, right)
    expected = (0.20 / (0.20 + 0.25 + 0.12 + 0.08)) * 25.0
    assert out["overall_pct"] == pytest.approx(expected, abs=0.01)


def test_empty_list_is_not_skipped():
    """[] vs populated counts as 100% drift for that class — not skipped."""
    right = {**BASELINE, "skills": []}
    out = compute_drift_score(BASELINE, right)
    assert out["skills"]["pct"] == 100.0
    # Skills weight 0.08, all other classes unchanged.
    assert out["overall_pct"] == pytest.approx(0.08 * 100.0, abs=0.01)


def test_headline_changes_capped_at_5():
    """Multiple changes — output limited to 5 bullets."""
    right = {
        "identity": {"name": "X", "location": "Y", "email": "z@z", "phone": "0"},
        **{k: v for k, v in BASELINE.items() if k != "identity"},
    }
    out = compute_drift_score(BASELINE, right)
    assert "headline_changes" in out
    assert len(out["headline_changes"]) <= 5
