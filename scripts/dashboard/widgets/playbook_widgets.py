"""Playbook widgets — the 5 playbook cards and the in-progress-runs widget.

Wires the Phase-1 playbook engine (scripts/playbooks/) into the canvas.
"""
import streamlit as st

from scripts.dashboard.handoff import handoff
from scripts.playbooks.definitions import get_playbook
from scripts.playbooks.runs import (
    start_run, list_active_runs, advance_run, abandon_run,
)
from scripts.playbooks.runner import evaluate_run


def active_run_rows(candidate_id: int) -> list[dict]:
    """Pure helper: describe each active run for display. Evaluates each run
    first (auto-advance), then returns display dicts."""
    rows = []
    for run in list_active_runs(candidate_id):
        evaluate_run(run.id)
    for run in list_active_runs(candidate_id):
        playbook = get_playbook(run.playbook_key)
        idx = min(run.current_step, len(playbook.steps) - 1)
        step = playbook.steps[idx]
        rows.append({
            "run_id": run.id,
            "playbook_label": playbook.label,
            "step_number": run.current_step + 1,
            "total_steps": len(playbook.steps),
            "step_label": step.label,
            "step_kind": step.kind,
            "step_command": step.command,
            "status": run.status,
        })
    return rows


def make_playbook_card_renderer(playbook_key: str):
    """Return a render(candidate) function for one playbook card."""
    def _render(candidate) -> None:
        playbook = get_playbook(playbook_key)
        with st.container(border=True):
            st.markdown(f"**{playbook.label}**")
            st.caption(" → ".join(s.label for s in playbook.steps))
            if st.button("Start", key=f"pb_start_{playbook_key}"):
                start_run(candidate.id, playbook_key)
                st.rerun()
    return _render


def render_in_progress_runs(candidate) -> None:
    """The in_progress_runs widget — active playbook runs with actions."""
    with st.container(border=True):
        st.markdown("**In progress**")
        rows = active_run_rows(candidate.id)
        if not rows:
            st.caption("No playbook in progress. Start one from a card above.")
            return
        for row in rows:
            st.markdown(
                f"{row['playbook_label']} — step {row['step_number']} of "
                f"{row['total_steps']}: *{row['step_label']}*"
            )
            cols = st.columns(3)
            with cols[0]:
                if row["step_command"]:
                    if st.button("Continue", key=f"pb_cont_{row['run_id']}"):
                        handoff(row["step_command"],
                                note=f"Playbook step: {row['step_label']}")
                else:
                    st.caption("in-dashboard step")
            with cols[1]:
                if st.button("Mark done →", key=f"pb_done_{row['run_id']}"):
                    advance_run(row["run_id"])
                    st.rerun()
            with cols[2]:
                if st.button("Abandon", key=f"pb_abandon_{row['run_id']}"):
                    abandon_run(row["run_id"])
                    st.rerun()
