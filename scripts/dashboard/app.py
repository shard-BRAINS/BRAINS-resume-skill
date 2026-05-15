"""Main Streamlit entry for the BRAINS Resume dashboard.

Run via the `brains-resume-dashboard` CLI entry point (see launch.py)
which invokes `streamlit run scripts/dashboard/app.py`.

This is the v1.3.0 stub — subsequent tasks fill in the data layer, styling,
seven tabs, and sidebar. For now, the app renders a title and a placeholder
message confirming the dashboard is reachable.
"""
import streamlit as st


def main() -> None:
    st.set_page_config(
        page_title="BRAINS Resume Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.title("BRAINS Resume Dashboard")
    st.caption("v1.3.0 — under construction")
    st.info(
        "Dashboard package skeleton is in place. Tab modules, sidebar, and "
        "data layer ship in later Plan 5b tasks."
    )


main()
