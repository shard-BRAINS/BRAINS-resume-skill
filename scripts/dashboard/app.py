"""Main Streamlit entry for the BRAINS Resume dashboard.

Run via the `brains-resume-dashboard` CLI entry point (see launch.py)
which invokes `streamlit run scripts/dashboard/app.py`.

Single-page top-tab layout matching the user's TSE Tools visual reference.
Seven tabs: Overview, Resumes, Cover Letters, JDs, Applications, Analytics,
Pacing. Persistent sidebar for profile editing. BRAINS Incubator branded.
"""
import streamlit as st

from scripts.dashboard.sidebar import render_sidebar
from scripts.dashboard.style import inject_brand_css
from scripts.dashboard.tabs import (
    analytics,
    applications,
    cover_letters,
    jds,
    overview,
    pacing,
    resumes,
    workflows,
)
from scripts.tracker.models import Profile
from scripts.tracker.profile import read_profile, write_profile


def require_user_name() -> None:
    """If profile.json is missing first_name or last_name, surface a
    one-shot modal.

    Skipped when there is no active Streamlit script-run context (e.g.
    during unit-test imports in bare mode) to avoid StreamlitAPIException.
    """
    from streamlit.runtime.scriptrunner import get_script_run_ctx

    if get_script_run_ctx() is None:
        return

    profile = read_profile()
    if profile.first_name and profile.last_name:
        return

    @st.dialog("Set your name to continue")
    def _name_modal():
        st.write(
            "BRAINS Resume uses your name in every artifact filename "
            "(e.g. `Matthew_Gell_resume_2026-05-19_KX7M9Q.docx`). "
            "Please set it once."
        )
        first = st.text_input("First name", value=profile.first_name or "")
        last = st.text_input("Last name", value=profile.last_name or "")
        if st.button("Save", type="primary"):
            if first.strip() and last.strip():
                profile.first_name = first.strip()
                profile.last_name = last.strip()
                write_profile(profile)
                st.rerun()
            else:
                st.error("Both first and last names are required.")

    _name_modal()


def main() -> None:
    st.set_page_config(
        page_title="BRAINS Resume Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_brand_css()
    render_sidebar()
    require_user_name()

    st.title("BRAINS Resume Dashboard")

    tabs = st.tabs([
        "Overview",
        "Resumes",
        "Cover Letters",
        "JDs",
        "Applications",
        "Analytics",
        "Pacing",
        "Workflows",
    ])

    with tabs[0]:
        overview.render()
    with tabs[1]:
        resumes.render()
    with tabs[2]:
        cover_letters.render()
    with tabs[3]:
        jds.render()
    with tabs[4]:
        applications.render()
    with tabs[5]:
        analytics.render()
    with tabs[6]:
        pacing.render()
    with tabs[7]:
        workflows.render()


main()
