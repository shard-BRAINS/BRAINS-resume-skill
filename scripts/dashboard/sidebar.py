"""Persistent sidebar — focus areas, healthy weekly rate, pacing notes, refresh."""
import subprocess

import streamlit as st

from scripts.dashboard.data import clear_all_caches
from scripts.dashboard.style import footer
from scripts.tracker.models import Profile
from scripts.tracker.profile import read_profile, write_profile


def render_sidebar() -> None:
    """Render the persistent sidebar. Called once from app.py before tabs."""
    with st.sidebar:
        st.markdown("### BRAINS Resume")
        st.markdown("*Dashboard*")
        st.markdown("---")

        profile = read_profile()

        # Focus areas
        st.markdown("**Focus areas**")
        focus_text = st.text_area(
            "Comma-separated",
            value=", ".join(profile.focus_areas),
            key="sidebar_focus_areas",
            label_visibility="collapsed",
        )

        # Healthy weekly rate
        st.markdown("**Healthy weekly rate**")
        rate = st.number_input(
            "Applications per week",
            min_value=0, max_value=100,
            value=profile.healthy_weekly_rate or 0,
            key="sidebar_rate",
            label_visibility="collapsed",
        )

        # Pacing notes
        st.markdown("**Sensory-load notes**")
        pacing_notes = st.text_area(
            "What's been overwhelming or sustainable",
            value=profile.pacing_notes or "",
            key="sidebar_pacing_notes",
            label_visibility="collapsed",
            height=120,
        )

        if st.button("Save profile", key="sidebar_save"):
            new_focus = [
                t.strip() for t in focus_text.split(",") if t.strip()
            ]
            new_rate = rate if rate > 0 else None
            new_notes = pacing_notes.strip() if pacing_notes.strip() else None
            write_profile(Profile(
                focus_areas=new_focus,
                healthy_weekly_rate=new_rate,
                pacing_notes=new_notes,
                log_handoffs=profile.log_handoffs,
            ))
            clear_all_caches()
            st.success("Profile saved.")
            st.rerun()

        st.markdown("---")
        if st.button("↻ Refresh all", key="sidebar_refresh_all"):
            clear_all_caches()
            st.rerun()

        _render_handoff_section(profile)

        st.markdown("---")
        st.caption(f"v1.3.0 · {_git_sha()}")
        footer()


def _render_handoff_section(profile: Profile) -> None:
    """Render the handoff-log toggle and recent-handoffs viewer."""
    import datetime
    from pathlib import Path

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
