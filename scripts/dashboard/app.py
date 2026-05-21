"""Main Streamlit entry for the BRAINS Resume dashboard.

Run via the `brains-resume-dashboard` CLI entry point (see launch.py)
which invokes `streamlit run scripts/dashboard/app.py`.

Eight-tab layout. The Home tab is a customizable widget canvas
(orchestration hub); the other seven are deep drill-down views.
BRAINS Incubator branded.
"""
import streamlit as st

from scripts.dashboard.sidebar import render_sidebar
from scripts.dashboard.style import inject_brand_css
from scripts.dashboard.tabs import (
    analytics,
    applications,
    cover_letters,
    drift as drift_tab,
    home,
    jds,
    pacing,
    resumes,
)
from scripts.tracker.candidates import list_candidates


def require_candidate() -> None:
    """If no candidate exists yet, surface a one-shot modal directing the
    user to create their first candidate via the sidebar."""
    from streamlit.runtime.scriptrunner import get_script_run_ctx

    if get_script_run_ctx() is None:
        return
    if list_candidates():
        return

    @st.dialog("Create a candidate to continue")
    def _candidate_modal():
        st.write(
            "BRAINS Resume organises every artifact under a candidate. "
            "Use the **+ New candidate** expander in the sidebar to create "
            "your first one."
        )
        st.info("Open the sidebar on the left and expand **+ New candidate**.")

    _candidate_modal()


def main() -> None:
    st.set_page_config(
        page_title="BRAINS Resume Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_brand_css()
    render_sidebar()
    require_candidate()

    st.title("BRAINS Resume Dashboard")

    tabs = st.tabs([
        "Home",
        "Resumes",
        "Cover Letters",
        "JDs",
        "Applications",
        "Analytics",
        "Pacing",
        "Drift",
    ])

    with tabs[0]:
        home.render()
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
        drift_tab.render()


main()
