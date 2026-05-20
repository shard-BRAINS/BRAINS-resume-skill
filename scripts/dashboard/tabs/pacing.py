"""Pacing tab — applications-this-week vs healthy rate + sensory-load notes."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from scripts.dashboard.data import cached_list_applications
from scripts.dashboard.prep.sparkline import applications_per_week_8w
from scripts.dashboard.prep.trends import applications_this_week_count
from scripts.dashboard.style import INCUBATOR_BLUE
from scripts.tracker.candidates import get_active_candidate


def render() -> None:
    active = get_active_candidate()
    if active is None:
        st.info(
            "No active candidate. Select or create one in the sidebar to see "
            "pacing."
        )
        return

    if st.button("↻ Refresh", key="pacing_refresh"):
        cached_list_applications.clear()

    rows = cached_list_applications()
    apps_this_week = applications_this_week_count(rows)
    target = active.healthy_weekly_rate

    # Tile: this-week count vs target
    col1, col2 = st.columns(2)
    col1.metric(
        "This week",
        f"{apps_this_week}" + (f" / {target}" if target is not None else ""),
        delta=(f"{apps_this_week - target:+d} vs target") if target is not None else None,
    )
    col2.metric(
        "Healthy weekly rate",
        f"{target}" if target is not None else "(not set)",
    )

    # Status banner
    st.markdown("---")
    if target is None:
        st.warning(
            "**No healthy weekly rate set.** Set one in the sidebar — the skill never "
            "recommends a number; you choose what your sensory bandwidth can sustain."
        )
    elif apps_this_week > target:
        st.warning(
            f"**{apps_this_week} applications this week — above your stated healthy "
            f"rate of {target}/week.** Consider pausing. No shame in slowing down."
        )
    elif apps_this_week == target:
        st.info(f"**At your healthy rate this week** ({apps_this_week} of {target}).")
    else:
        st.success(
            f"**Under your healthy rate this week** ({apps_this_week} of {target}). "
            "Bandwidth available if you want to use it."
        )

    # 8-week pacing trend
    st.markdown("---")
    st.subheader("8-week pacing trend")
    weekly_data = applications_per_week_8w(rows)
    df = pd.DataFrame(weekly_data)
    fig = go.Figure(
        go.Bar(
            x=df["week_starting"],
            y=df["count"],
            marker_color=INCUBATOR_BLUE,
        )
    )
    if target is not None:
        fig.add_hline(
            y=target, line_dash="dash",
            line_color="#E0A040",
            annotation_text=f"target ({target}/wk)", annotation_position="right",
        )
    fig.update_layout(
        height=240,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title="Week starting",
        yaxis_title="Applications",
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Sensory-load notes — read-only in this tab; edited from sidebar
    st.markdown("---")
    st.subheader("Sensory-load notes")
    if active.pacing_notes:
        st.markdown(active.pacing_notes)
    else:
        st.caption(
            "Edit your sensory-load notes in the sidebar. Track what's been "
            "overwhelming and what's been sustainable across weeks."
        )
