"""Main Streamlit entry for the BRAINS Resume dashboard.

Run via the `brains-resume-dashboard` CLI entry point (see launch.py)
which invokes `streamlit run scripts/dashboard/app.py`.

Single-page top-tab layout matching the user's TSE Tools visual reference.
Nine tabs: Overview, Resumes, Cover Letters, JDs, Applications, Analytics,
Pacing, Workflows, Drift. Persistent sidebar for profile editing.
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
    jds,
    overview,
    pacing,
    resumes,
    workflows,
)
from scripts.tracker.candidates import list_candidates


def require_candidate() -> None:
    """If no candidate exists yet, surface a one-shot modal directing the
    user to create their first candidate via the sidebar.

    Under Approach B, every artifact is owned by a candidate, so the
    dashboard needs at least one candidate before it is usable. The
    sidebar already provides a '+ New candidate' expander; this modal
    simply blocks and points the user there.

    Skipped when there is no active Streamlit script-run context (e.g.
    during unit-test imports in bare mode) to avoid StreamlitAPIException.
    """
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
            "your first one — the candidate's name is used in every "
            "artifact filename "
            "(e.g. `Matthew_Gell_resume_2026-05-20_KX7M9Q.docx`)."
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
        "Overview",
        "Resumes",
        "Cover Letters",
        "JDs",
        "Applications",
        "Analytics",
        "Pacing",
        "Workflows",
        "Drift",
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
    with tabs[8]:
        drift_tab.render()


main()
