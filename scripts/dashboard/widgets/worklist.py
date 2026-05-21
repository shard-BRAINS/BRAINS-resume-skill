"""The worklist widget — a computed 'what to do next' list.

compute_worklist applies three concrete rules against the tracker DB:
  1. active playbook runs            -> "Continue: <playbook>"   (high)
  2. applications submitted > 7 days ago with no outcome  (medium)
  3. below-target weekly pacing                            (low)
"""
from datetime import datetime, timedelta

import streamlit as st

from scripts.dashboard.data import cached_list_applications, cached_weekly_summary
from scripts.playbooks.definitions import get_playbook
from scripts.playbooks.runs import list_active_runs


_SEVERITY_DOT = {"high": "🔴", "medium": "🟠", "low": "🟡"}


def compute_worklist(candidate_id: int) -> list[dict]:
    """Return prioritized next-action items: list of
    {severity, text} dicts, high severity first."""
    items: list[dict] = []

    for run in list_active_runs(candidate_id):
        playbook = get_playbook(run.playbook_key)
        items.append({
            "severity": "high",
            "text": f"Continue: {playbook.label} "
                    f"(step {run.current_step + 1} of {len(playbook.steps)})",
        })

    rows = cached_list_applications()
    cutoff = datetime.now() - timedelta(days=7)
    for r in rows:
        if r.latest_outcome is None and datetime.fromisoformat(r.submitted_at) < cutoff:
            days = (datetime.now() - datetime.fromisoformat(r.submitted_at)).days
            items.append({
                "severity": "medium",
                "text": f"{r.company} — {days} days, no response",
            })

    weekly = cached_weekly_summary()
    if weekly.pacing_vs_target == "below":
        items.append({
            "severity": "low",
            "text": f"Pacing — {weekly.applications_count} applications this week",
        })

    order = {"high": 0, "medium": 1, "low": 2}
    items.sort(key=lambda it: order[it["severity"]])
    return items


def render_worklist(candidate) -> None:
    """The worklist widget."""
    with st.container(border=True):
        st.markdown("**Next actions**")
        items = compute_worklist(candidate.id)
        if not items:
            st.caption("Nothing needs attention right now.")
            return
        for it in items:
            st.markdown(f"{_SEVERITY_DOT[it['severity']]} {it['text']}")
