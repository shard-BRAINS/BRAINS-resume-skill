"""Persistent sidebar — candidate picker, refresh, handoff log."""
import subprocess

import streamlit as st

from scripts.dashboard.data import clear_all_caches
from scripts.dashboard.style import footer
from scripts.tracker.models import Profile
from scripts.tracker.profile import read_profile
from scripts.tracker.candidates import (
    create_candidate,
    get_active_candidate,
    list_candidates,
    set_active_candidate,
    update_candidate,
)


def _resolve_picker_default_index(candidates: list, active_id) -> int:
    """Return the selectbox index of the active candidate, or 0 as a fallback."""
    if not candidates:
        return 0
    if active_id is None:
        return 0
    for i, c in enumerate(candidates):
        if c.id == active_id:
            return i
    return 0


def render_sidebar() -> None:
    """Render the persistent sidebar. Called once from app.py before tabs."""
    from scripts.outputs.io import get_outputs_root

    with st.sidebar:
        st.markdown("### BRAINS Resume")
        st.markdown("*Dashboard*")
        st.markdown("---")

        profile = read_profile()

        # Candidate picker
        st.subheader("Candidate")
        _render_candidate_picker()

        st.caption(f"Outputs: `{get_outputs_root()}`")

        st.markdown("---")
        if st.button("↻ Refresh all", key="sidebar_refresh_all"):
            clear_all_caches()
            st.rerun()

        _render_handoff_section(profile)

        st.markdown("---")
        st.caption(f"v1.3.0 · {_git_sha()}")
        footer()


# Public alias — the rewritten entry point name.
render = render_sidebar


def _render_candidate_picker() -> None:
    """Render the candidate selectbox + new/edit expanders."""
    candidates = list_candidates()
    active = get_active_candidate()
    labels = [f"{c.first_name} {c.last_name}".strip() for c in candidates]

    if labels:
        default_idx = _resolve_picker_default_index(
            candidates, active.id if active else None
        )
        selection = st.selectbox(
            "Candidate",
            options=labels,
            index=default_idx,
            key="sidebar_candidate_picker",
            label_visibility="collapsed",
        )
        if selection:
            chosen = candidates[labels.index(selection)]
            if active is None or chosen.id != active.id:
                set_active_candidate(chosen.id)
                clear_all_caches()
                st.rerun()
    else:
        st.caption("No candidates yet — create one below.")

    _render_new_candidate_expander()

    if active is not None:
        _render_edit_candidate_expander(active)


def _render_new_candidate_expander() -> None:
    """Render the '+ New candidate' expander."""
    with st.expander("+ New candidate"):
        new_first = st.text_input("First name", key="new_first")
        new_last = st.text_input("Last name", key="new_last")
        new_focus_raw = st.text_area(
            "Focus areas (one per line)", key="new_focus"
        )
        new_rate = st.number_input(
            "Healthy weekly rate", min_value=0, step=1, key="new_rate"
        )
        new_notes = st.text_area("Pacing notes (optional)", key="new_notes")
        if st.button("Create candidate", key="new_candidate_create"):
            focus = [
                line.strip()
                for line in (new_focus_raw or "").splitlines()
                if line.strip()
            ]
            cid = create_candidate(
                first_name=new_first,
                last_name=new_last,
                focus_areas=focus,
                healthy_weekly_rate=int(new_rate) if new_rate else None,
                pacing_notes=new_notes or None,
            )
            set_active_candidate(cid)
            clear_all_caches()
            st.rerun()


def _render_edit_candidate_expander(active) -> None:
    """Render the 'Edit selected' expander, pre-populated from the active candidate."""
    with st.expander("Edit selected"):
        edit_first = st.text_input(
            "First name", value=active.first_name or "", key="edit_first"
        )
        edit_last = st.text_input(
            "Last name", value=active.last_name or "", key="edit_last"
        )
        edit_focus_raw = st.text_area(
            "Focus areas (one per line)",
            value="\n".join(active.focus_areas),
            key="edit_focus",
        )
        edit_rate = st.number_input(
            "Healthy weekly rate",
            min_value=0,
            step=1,
            value=active.healthy_weekly_rate or 0,
            key="edit_rate",
        )
        edit_notes = st.text_area(
            "Pacing notes (optional)",
            value=active.pacing_notes or "",
            key="edit_notes",
        )
        if st.button("Save changes", key="edit_candidate_save"):
            focus = [
                line.strip()
                for line in (edit_focus_raw or "").splitlines()
                if line.strip()
            ]
            update_candidate(
                active.id,
                first_name=edit_first,
                last_name=edit_last,
                focus_areas=focus,
                healthy_weekly_rate=int(edit_rate) if edit_rate else None,
                pacing_notes=edit_notes or None,
            )
            clear_all_caches()
            st.success("Candidate updated.")
            st.rerun()


def _render_handoff_section(profile: Profile) -> None:
    """Render the handoff-log toggle and recent-handoffs viewer."""
    import datetime

    from scripts.dashboard import handoff

    st.markdown("---")
    st.markdown("**Handoff log**")
    new_value = st.checkbox(
        "Log handoffs to disk",
        value=profile.log_handoffs,
        key="sidebar_log_handoffs",
        help=f"Writes one .txt per handoff to {handoff.HANDOFF_LOG_DIR}",
    )
    if new_value != profile.log_handoffs:
        from scripts.tracker import profile as profile_io
        profile.log_handoffs = new_value
        profile_io.write_profile(profile)
        st.toast("Handoff-log preference saved.", icon="✅")

    with st.expander("Recent handoffs (last 10)"):
        if not handoff.HANDOFF_LOG_DIR.exists():
            st.caption("_No handoffs logged yet._")
            return
        files = sorted(handoff.HANDOFF_LOG_DIR.glob("*.txt"), reverse=True)[:10]
        if not files:
            st.caption("_No handoffs logged yet._")
            return
        for f in files:
            ts = datetime.datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            st.caption(f"`{f.name}` — {ts}")


def _git_sha() -> str:
    """Return the short git SHA of the current HEAD, or 'unknown' on failure."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=2,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.SubprocessError, OSError, FileNotFoundError):
        pass
    return "unknown"
