"""The Home tab — the customizable widget canvas.

When the active candidate has not completed onboarding, the resume-first
onboarding surface is rendered above the canvas. Otherwise the canvas
renders normally: all 'upper'-zone widgets, then all 'lower'-zone widgets.
A Customize expander edits the layout.
"""
import streamlit as st

from scripts.tracker.candidates import get_active_candidate
from scripts.dashboard.widgets.catalog import resolve_layout
from scripts.dashboard.widgets.layout import get_saved_layout
from scripts.dashboard.widgets.customize import render_customize
from scripts.dashboard.widgets.onboarding import onboarding_needed, render_onboarding


def effective_layout(candidate_id: int):
    """Return the resolved layout for a candidate — list of (Widget, enabled)."""
    return resolve_layout(get_saved_layout(candidate_id))


def render() -> None:
    """Render the Home tab."""
    active = get_active_candidate()
    if active is None:
        st.info("No active candidate. Select or create one in the sidebar.")
        return

    if onboarding_needed(active):
        render_onboarding(active)
        st.markdown("---")

    with st.expander("⚙ Customize"):
        render_customize(active)

    layout = effective_layout(active.id)
    upper = [w for w, en in layout if en and w.zone == "upper"]
    lower = [w for w, en in layout if en and w.zone == "lower"]

    for widget in upper:
        widget.render(active)
    if upper and lower:
        st.markdown("---")
    for widget in lower:
        widget.render(active)
