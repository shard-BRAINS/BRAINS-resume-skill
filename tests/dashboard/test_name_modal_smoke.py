"""Smoke checks for the sidebar candidate picker + first-use modal.

Approach B replaced the profile name fields (first_name/last_name) with a
candidate picker. These tests assert the candidate-model surface instead.
"""
from pathlib import Path


def test_sidebar_has_candidate_picker():
    """The sidebar exposes the candidate-picker surface, not the old name fields."""
    src = Path("scripts/dashboard/sidebar.py").read_text(encoding="utf-8")
    assert "sidebar_candidate_picker" in src
    assert "+ New candidate" in src
    assert "Edit selected" in src
    assert "Outputs:" in src
    # The old per-profile name widgets must be gone.
    assert "sidebar_first_name" not in src
    assert "sidebar_last_name" not in src


def test_app_has_require_candidate():
    """The first-use gate requires at least one candidate, not a profile name."""
    src = Path("scripts/dashboard/app.py").read_text(encoding="utf-8")
    assert "def require_candidate" in src
    assert "st.dialog" in src
    assert "list_candidates" in src
    # The old profile-name gate must be gone.
    assert "first_name" not in src
    assert "last_name" not in src
