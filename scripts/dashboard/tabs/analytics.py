"""Analytics tab — efficacy charts by template and channel."""
import pandas as pd
import plotly.express as px
import streamlit as st

from scripts.dashboard.data import (
    cached_efficacy_by_template,
    cached_list_applications,
)
from scripts.dashboard.style import INCUBATOR_BLUE


def render() -> None:
    if st.button("↻ Refresh", key="analytics_refresh"):
        cached_efficacy_by_template.clear()
        cached_list_applications.clear()

    st.subheader("Efficacy by template")
    _render_efficacy_by_template()

    st.markdown("---")
    st.subheader("Efficacy by channel")
    _render_efficacy_by_channel()


def _render_efficacy_by_template() -> None:
    rows = cached_efficacy_by_template()
    if not rows:
        st.info("No data yet — register applications via `/brains-precheck` or `/brains-track add`.")
        return

    df = pd.DataFrame([
        {
            "template": r.template,
            "submitted": r.submitted_count,
            "callbacks": r.callback_count,
            "interviews": r.interview_count,
            "offers": r.offer_count,
            "rejections": r.rejection_count,
        }
        for r in rows
    ])

    fig = px.bar(
        df.melt(id_vars="template", var_name="stage", value_name="count"),
        x="template", y="count", color="stage",
        barmode="group",
        color_discrete_sequence=[INCUBATOR_BLUE, "#7ABA7A", "#5A8FE8", "#A070C0", "#C76060"],
    )
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_efficacy_by_channel() -> None:
    """Aggregate applications by channel + outcome class for a stacked-bar view."""
    rows = cached_list_applications()
    if not rows:
        st.caption("No applications to analyze yet.")
        return

    interview_types = {"phone_screen", "first_round", "second_round", "take_home"}
    counts: dict = {}
    for r in rows:
        ch = r.channel
        bucket = counts.setdefault(ch, {"submitted": 0, "callbacks": 0,
                                       "interviews": 0, "offers": 0,
                                       "rejections": 0})
        bucket["submitted"] += 1
        if r.latest_outcome == "callback":
            bucket["callbacks"] += 1
        elif r.latest_outcome in interview_types:
            bucket["interviews"] += 1
        elif r.latest_outcome == "offer":
            bucket["offers"] += 1
        elif r.latest_outcome == "rejection":
            bucket["rejections"] += 1

    df = pd.DataFrame([{"channel": ch, **vals} for ch, vals in counts.items()])

    fig = px.bar(
        df.melt(id_vars="channel", var_name="stage", value_name="count"),
        x="channel", y="count", color="stage",
        barmode="group",
        color_discrete_sequence=[INCUBATOR_BLUE, "#7ABA7A", "#5A8FE8", "#A070C0", "#C76060"],
    )
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)
