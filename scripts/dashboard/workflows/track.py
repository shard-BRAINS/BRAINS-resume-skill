"""/brains-track — full tracker CRUD in-dashboard (no LLM handoff needed)."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Optional

import streamlit as st

from scripts.tracker import add as tracker_add, query as tracker_query

EVENT_TYPES = [
    "acknowledged", "callback", "phone_screen", "first_round", "second_round",
    "take_home", "offer", "rejection", "ghosted", "withdrew",
]


def render(file_path: Optional[Path] = None) -> None:
    st.markdown("**Manage the application tracker.**")
    st.caption("Fully in-dashboard — no Claude Code handoff for tracker actions.")

    apps = tracker_query.list_applications()
    if not apps:
        st.info("No applications tracked yet. Use the Pre-application workflow to register the first one.")
        return

    options = {f"#{a.id} — {a.company} / {a.role_title}": a.id for a in apps}
    selected_label = st.selectbox("Pick an application", options=list(options.keys()), key="track_pick")
    app_id = options[selected_label]

    event_type = st.selectbox("Event type", EVENT_TYPES, key="track_event")
    event_date = st.date_input("Date", value=date.today(), key="track_date")
    notes = st.text_input("Notes (optional)", key="track_notes")

    if st.button("Log outcome", key="track_log_btn"):
        try:
            event_dt = datetime.combine(event_date, datetime.min.time())
            tracker_add.record_outcome(
                application_id=app_id,
                event_type=event_type,
                event_date=event_dt,
                notes=notes or None,
            )
            st.success(f"Logged `{event_type}` on application #{app_id}.")
        except Exception as e:
            st.error(f"Failed to log outcome: {e}")
