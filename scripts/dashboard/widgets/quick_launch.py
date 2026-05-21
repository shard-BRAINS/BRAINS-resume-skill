"""The quick_launch widget — standalone workflows not part of any playbook.

Each entry reuses an existing workflow module's render(file_path, key_prefix).
"""
import streamlit as st

from scripts.dashboard.workflows import deai, disclosure, jd_analyze, track


# (slug, label, module)
QUICK_LAUNCH_WORKFLOWS = (
    ("jd_analyze", "Analyze a JD", jd_analyze),
    ("deai", "De-AI scan", deai),
    ("disclosure", "Disclosure coaching", disclosure),
    ("track", "Application tracker", track),
)


def render_quick_launch(candidate) -> None:
    """The quick_launch widget."""
    with st.container(border=True):
        st.markdown("**Quick launch**")
        for slug, label, module in QUICK_LAUNCH_WORKFLOWS:
            with st.expander(label):
                module.render(file_path=None, key_prefix=f"ql_{slug}")
