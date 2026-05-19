"""Smoke checks for Tasks 19+20 (sidebar name fields + first-use modal)."""
from pathlib import Path


def test_sidebar_has_name_fields():
    src = Path("scripts/dashboard/sidebar.py").read_text(encoding="utf-8")
    assert "First name" in src
    assert "Last name" in src
    assert "sidebar_first_name" in src
    assert "sidebar_last_name" in src
    assert "Outputs:" in src


def test_app_has_require_user_name():
    src = Path("scripts/dashboard/app.py").read_text(encoding="utf-8")
    assert "def require_user_name" in src
    assert "st.dialog" in src
