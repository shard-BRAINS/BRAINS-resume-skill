"""Smoke test: the dashboard app module imports without errors.

Catches missing-module errors, import-cycle issues, and syntax errors.
Does NOT render the app — that's what test_app_overview_render.py does.
"""


def test_app_module_imports():
    # Importing the module triggers Streamlit's set_page_config and main() call.
    # Without a Streamlit runtime context, these calls warn but do not raise.
    import scripts.dashboard.app  # noqa: F401


def test_all_tab_modules_import():
    from scripts.dashboard.tabs import (  # noqa: F401
        analytics, applications, cover_letters, jds, overview, pacing, resumes,
    )


def test_sidebar_module_imports():
    from scripts.dashboard.sidebar import render_sidebar  # noqa: F401


def test_style_module_imports():
    from scripts.dashboard.style import inject_brand_css, footer  # noqa: F401
