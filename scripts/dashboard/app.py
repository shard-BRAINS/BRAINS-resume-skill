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
)


def main() -> None:
    st.set_page_config(
        page_title="BRAINS Resume Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_brand_css()
    render_sidebar()

    st.title("BRAINS Resume Dashboard")

    tabs = st.tabs([
        "Overview",
        "Resumes",
        "Cover Letters",
        "JDs",
        "Applications",
        "Analytics",
        "Pacing",
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


main()
