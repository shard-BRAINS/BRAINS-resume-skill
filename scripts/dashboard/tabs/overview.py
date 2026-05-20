"""Overview tab — the dashboard's landing page.

Top-to-bottom:
  1. Summary tile row (Applications / Callbacks / Interviews / Offers / Pacing)
  2. Mini sparkline cards (Apps-per-week, Callback rate trend)
  3. Idle-state callouts when applicable
  4. Plotly funnel chart
  5. Twin side-by-side panels (Pending callbacks, Recent interview activity)
"""
from datetime import datetime, timedelta

import plotly.graph_objects as go
import streamlit as st

from scripts.dashboard.data import (
    cached_list_applications,
    cached_weekly_summary,
)
from scripts.dashboard.prep.funnel import compute_funnel_data
from scripts.dashboard.prep.idle_states import detect_idle_states
from scripts.dashboard.prep.sparkline import (
    applications_per_week_8w,
    callback_rate_rolling_30d,
)
from scripts.dashboard.prep.trends import (
    applications_this_week_count,
    callback_count_last_n_days,
    interview_count_last_n_days,
)
from scripts.dashboard.style import INCUBATOR_BLUE
from scripts.tracker.candidates import get_active_candidate


INTERVIEW_EVENT_TYPES = {"phone_screen", "first_round", "second_round", "take_home"}
TERMINAL_OUTCOMES = {"offer", "rejection", "withdrew"}


def _summary_counts() -> dict:
    """Return active-candidate-scoped headline counts for the Overview tab.

    Pure helper (no Streamlit) so it can be unit-tested directly. The tracker
    query functions auto-scope to the active candidate (Task 7), so no
    candidate_id argument is needed here.
    """
    from scripts.tracker.query import list_applications, list_jds
    return {
        "jds": len(list_jds()),
        "applications": len(list_applications()),
    }


def render() -> None:
    """Render the Overview tab content."""
    active = get_active_candidate()
    if active is None:
        st.info(
            "No active candidate. Select or create one in the sidebar to see "
            "the overview."
        )
        return

    if st.button("↻ Refresh", key="overview_refresh"):
        cached_list_applications.clear()
        cached_weekly_summary.clear()

    rows = cached_list_applications()
    weekly = cached_weekly_summary()
    now = datetime.now()

    # Drift surfaces scope by candidate_id (Task 15).
    scope = {"candidate_id": active.id}

    _render_summary_tiles(rows, weekly, active, now)
    render_drift_tile(scope)
    st.markdown("---")
    _render_sparkline_cards(rows, now)
    st.markdown("---")
    _render_idle_states(rows, now)
    _render_funnel(rows)
    st.markdown("---")
    _render_twin_panels(rows, now)


def _render_summary_tiles(rows, weekly, candidate, now) -> None:
    """Five-tile row: Applications / Callbacks / Interviews / Offers / Pacing."""
    total_apps = len(rows)
    callbacks_lifetime = sum(1 for r in rows if r.latest_outcome == "callback")
    callbacks_last_30 = callback_count_last_n_days(rows, days=30, now=now)
    interviews_last_30 = interview_count_last_n_days(rows, days=30, now=now)
    offers_lifetime = sum(1 for r in rows if r.latest_outcome == "offer")
    apps_this_week = applications_this_week_count(rows, now=now)

    callback_rate = (callbacks_lifetime / total_apps * 100) if total_apps else 0
    interview_rate = (
        sum(1 for r in rows if r.latest_outcome in INTERVIEW_EVENT_TYPES)
        / total_apps * 100
    ) if total_apps else 0

    target = candidate.healthy_weekly_rate if candidate else None
    pacing_label = f"{apps_this_week}"
    if target is not None:
        pacing_label = f"{apps_this_week} / {target}"
        delta = apps_this_week - target
        pacing_delta = f"{delta:+d} vs target"
    else:
        pacing_delta = "no target set"

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric(label="Applications", value=total_apps, delta=f"{apps_this_week} this week")
    col2.metric(
        label="Callbacks",
        value=callbacks_lifetime,
        delta=f"{callback_rate:.0f}% rate",
    )
    col3.metric(
        label="Interviews",
        value=interviews_last_30,
        delta=f"{interview_rate:.0f}% rate",
    )
    col4.metric(label="Offers", value=offers_lifetime)
    col5.metric(label="Pacing (this week)", value=pacing_label, delta=pacing_delta)


def _render_sparkline_cards(rows, now) -> None:
    """Two sparkline cards: apps-per-week, callback-rate trend."""
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Applications per week (last 8 weeks)**")
        data = applications_per_week_8w(rows, now=now)
        fig = go.Figure(
            go.Bar(
                x=[d["week_starting"] for d in data],
                y=[d["count"] for d in data],
                marker_color=INCUBATOR_BLUE,
            )
        )
        fig.update_layout(
            height=140,
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("**Callback rate (rolling 30d)**")
        data = callback_rate_rolling_30d(rows, now=now)
        if not data:
            st.caption("Not enough data yet — submit more applications to see a trend.")
        else:
            fig = go.Figure(
                go.Scatter(
                    x=[d["date"] for d in data],
                    y=[d["rate"] for d in data],
                    mode="lines",
                    line=dict(color=INCUBATOR_BLUE, width=2),
                )
            )
            fig.update_layout(
                height=140,
                margin=dict(l=0, r=0, t=0, b=0),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
                yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)


def _render_idle_states(rows, now) -> None:
    callouts = detect_idle_states(rows, now=now)
    for c in callouts:
        st.success(c)


def _render_funnel(rows) -> None:
    st.subheader("Application funnel")
    data = compute_funnel_data(rows)
    fig = go.Figure(
        go.Funnel(
            y=list(data.keys()),
            x=list(data.values()),
            marker={"color": [INCUBATOR_BLUE, INCUBATOR_BLUE, INCUBATOR_BLUE, INCUBATOR_BLUE, "#5A3A3A"]},
        )
    )
    fig.update_layout(
        height=320,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_twin_panels(rows, now) -> None:
    """Pending callbacks (left) and Recent interview activity (right)."""
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Pending callbacks")
        cutoff = now - timedelta(days=30)
        pending = [
            r for r in rows
            if datetime.fromisoformat(r.submitted_at) >= cutoff
            and r.latest_outcome is None
        ]
        if not pending:
            st.caption("Nothing pending in the last 30 days.")
        else:
            for r in pending[:10]:
                days_since = (now - datetime.fromisoformat(r.submitted_at)).days
                st.markdown(
                    f"**{r.company}** — {r.role_title} · {days_since}d ago · {r.channel}"
                )

    with col_right:
        st.subheader("Recent interview activity")
        recent_cutoff = now - timedelta(days=14)
        recent = [
            r for r in rows
            if r.latest_outcome in INTERVIEW_EVENT_TYPES
        ]
        if not recent:
            st.caption("No interview events in the last 14 days.")
        else:
            for r in recent[:10]:
                st.markdown(
                    f"**{r.company}** — {r.role_title} · {r.latest_outcome}"
                )


def _drift_tile_summary(scope: dict) -> dict:
    """Pure helper: return the data the drift trajectory tile renders.

    Returns:
        headline_pct: float | None — overall_pct of the most-recent resume,
            or None if the most-recent IS the baseline or no scored resume exists.
        sparkline: list[float | None] — last 12 vs_baseline overall_pct values,
            oldest first, with None for the baseline row.
        headline_changes: list[str] — top headline_changes from the latest
            non-baseline score.
        count: int — number of resumes in the lineage.
    """
    from scripts.dashboard.prep.drift_sparkline import drift_trajectory_last_n

    points = drift_trajectory_last_n(scope, n=12)
    if not points:
        return {"headline_pct": None, "sparkline": [], "headline_changes": [], "count": 0}

    latest = points[-1]
    headline_pct = latest["overall_pct"]
    sparkline = [p["overall_pct"] for p in points]

    # Latest version's headline_changes (read from the stored score).
    import json
    from scripts.tracker.db import open_db
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT vs_baseline_score FROM resume_drift_scores WHERE artifact_uid=?",
            (latest["artifact_uid"],),
        ).fetchone()
    finally:
        conn.close()
    headline_changes = []
    if row and row[0]:
        try:
            headline_changes = json.loads(row[0]).get("headline_changes", [])
        except json.JSONDecodeError:
            pass

    return {
        "headline_pct": headline_pct,
        "sparkline": sparkline,
        "headline_changes": headline_changes,
        "count": len(points),
    }


def render_drift_tile(scope: dict) -> None:
    """Render the drift trajectory tile in the Overview layout.

    Called from the main render() function alongside the other summary tiles.
    """
    summary = _drift_tile_summary(scope)
    with st.container(border=True):
        st.caption("Drift from baseline · active candidate")
        if summary["headline_pct"] is None:
            st.markdown("**—**")
            st.caption("No baseline yet")
            return
        st.markdown(f"**{summary['headline_pct']:.1f}%**")
        if summary["sparkline"]:
            # Use Streamlit's line_chart for a minimal sparkline.
            import pandas as pd
            chart_data = pd.DataFrame({
                "drift": [v if v is not None else 0.0 for v in summary["sparkline"]],
            })
            st.line_chart(chart_data, height=60, use_container_width=True)
        if summary["headline_changes"]:
            st.caption(summary["headline_changes"][0])
