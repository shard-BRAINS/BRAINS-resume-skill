"""Reporting tile widgets: pacing, drift, library counts, recent outcomes.

drift_tile_summary / render_tile_drift are relocated from the deleted
overview.py (their behaviour is unchanged).
"""
import json

import streamlit as st

from scripts.dashboard.data import cached_list_applications, cached_weekly_summary
from scripts.dashboard.prep.trends import applications_this_week_count
from scripts.tracker.candidates import get_candidate
from scripts.tracker.db import open_db


# ---- pacing -----------------------------------------------------------------

def pacing_summary(candidate_id: int) -> dict:
    """Return {this_week, target} for the active candidate's pacing."""
    candidate = get_candidate(candidate_id)
    rows = cached_list_applications()
    return {
        "this_week": applications_this_week_count(rows),
        "target": candidate.healthy_weekly_rate if candidate else None,
    }


def render_tile_pacing(candidate) -> None:
    with st.container(border=True):
        s = pacing_summary(candidate.id)
        value = str(s["this_week"])
        if s["target"] is not None:
            value = f"{s['this_week']} / {s['target']}"
        st.metric("Pacing (this week)", value)


# ---- library counts ---------------------------------------------------------

def library_counts(candidate_id: int) -> dict:
    """Return {resumes, cover_letters, jds} counts for the candidate."""
    conn = open_db()
    try:
        def _count(table):
            return conn.execute(
                f"SELECT COUNT(*) FROM {table} "
                "WHERE candidate_id=? AND archived_at IS NULL",
                (candidate_id,),
            ).fetchone()[0]
        return {
            "resumes": _count("resume_versions"),
            "cover_letters": _count("cover_letters"),
            "jds": _count("jds"),
        }
    finally:
        conn.close()


def render_tile_library_counts(candidate) -> None:
    with st.container(border=True):
        st.markdown("**Library**")
        c = library_counts(candidate.id)
        cols = st.columns(3)
        cols[0].metric("Resumes", c["resumes"])
        cols[1].metric("Cover letters", c["cover_letters"])
        cols[2].metric("JDs", c["jds"])


# ---- drift ------------------------------------------------------------------

def drift_tile_summary(scope: dict) -> dict:
    """Return {headline_pct, sparkline, headline_changes, count} for the
    drift trajectory tile. Relocated verbatim from overview._drift_tile_summary."""
    from scripts.dashboard.prep.drift_sparkline import drift_trajectory_last_n

    points = drift_trajectory_last_n(scope, n=12)
    if not points:
        return {"headline_pct": None, "sparkline": [], "headline_changes": [], "count": 0}
    latest = points[-1]
    headline_pct = latest["overall_pct"]
    sparkline = [p["overall_pct"] for p in points]
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


def render_tile_drift(candidate) -> None:
    with st.container(border=True):
        st.caption("Drift from baseline · active candidate")
        summary = drift_tile_summary({"candidate_id": candidate.id})
        if summary["headline_pct"] is None:
            st.markdown("**—**")
            st.caption("No baseline yet")
            return
        st.markdown(f"**{summary['headline_pct']:.1f}%**")
        if summary["sparkline"]:
            import pandas as pd
            st.line_chart(
                pd.DataFrame({"drift": [v if v is not None else 0.0
                                        for v in summary["sparkline"]]}),
                height=60, use_container_width=True,
            )
        if summary["headline_changes"]:
            st.caption(summary["headline_changes"][0])


# ---- recent outcomes --------------------------------------------------------

def render_tile_recent_outcomes(candidate) -> None:
    with st.container(border=True):
        st.markdown("**Recent outcomes**")
        rows = [r for r in cached_list_applications() if r.latest_outcome]
        if not rows:
            st.caption("No outcomes logged yet.")
            return
        for r in rows[:6]:
            st.markdown(f"- **{r.company}** — {r.latest_outcome}")
