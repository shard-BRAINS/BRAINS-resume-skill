"""Applications tab — sortable table of applications with filters."""
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from scripts.dashboard.data import cached_list_applications


def render() -> None:
    if st.button("↻ Refresh", key="apps_refresh"):
        cached_list_applications.clear()

    # Filter row
    filt_col1, filt_col2, filt_col3, filt_col4 = st.columns([2, 1, 1, 1])
    with filt_col1:
        company_filter = st.text_input(
            "Company filter",
            placeholder="leave blank for all",
            key="apps_company_filter",
        )
    with filt_col2:
        status_filter = st.selectbox(
            "Status", options=["all", "open", "closed"], index=0, key="apps_status_filter",
        )
    with filt_col3:
        days_filter = st.number_input(
            "Submitted in last N days",
            min_value=0, max_value=3650, value=365,
            key="apps_days_filter",
        )
    with filt_col4:
        channel_filter = st.selectbox(
            "Channel",
            options=["all", "linkedin", "agency", "direct", "referral", "other"],
            index=0,
            key="apps_channel_filter",
        )

    since = datetime.now() - timedelta(days=days_filter) if days_filter > 0 else None
    rows = cached_list_applications(
        company=company_filter if company_filter else None,
        since=since,
        status=status_filter if status_filter != "all" else None,
    )

    if channel_filter != "all":
        rows = [r for r in rows if r.channel == channel_filter]

    if not rows:
        st.info("No applications match the current filters.")
        return

    now = datetime.now()
    df = pd.DataFrame([
        {
            "id": r.id,
            "company": r.company,
            "role": r.role_title,
            "submitted": r.submitted_at[:10] if r.submitted_at else "",
            "channel": r.channel,
            "agency": r.agency_name or "",
            "resume_id": r.resume_version_id,
            "cover_letter_id": r.cover_letter_id,
            "latest_outcome": r.latest_outcome or "(pending)",
            "days_since": _days_since(r.submitted_at, now),
        }
        for r in rows
    ])

    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "company": st.column_config.TextColumn("Company", width="medium"),
            "role": st.column_config.TextColumn("Role", width="medium"),
            "submitted": st.column_config.TextColumn("Submitted", width="small"),
            "channel": st.column_config.TextColumn("Channel", width="small"),
            "agency": st.column_config.TextColumn("Agency", width="small"),
            "resume_id": st.column_config.NumberColumn("Resume", width="small"),
            "cover_letter_id": st.column_config.NumberColumn("CL", width="small"),
            "latest_outcome": st.column_config.TextColumn("Outcome", width="small"),
            "days_since": st.column_config.NumberColumn("Days", width="small"),
        },
        hide_index=True,
    )
    st.caption(
        f"Showing {len(df)} applications. To log an outcome: "
        "`/brains-track update <id> <event-type>` in your terminal."
    )

    # Inline workflow actions (v1.4.0)
    st.markdown("---")
    st.subheader("Log a new outcome")
    from scripts.dashboard.workflows import track as wf_track
    wf_track.render(file_path=None)


def _days_since(submitted_at: str, now: datetime) -> int:
    if not submitted_at:
        return 0
    try:
        return (now - datetime.fromisoformat(submitted_at)).days
    except (ValueError, TypeError):
        return 0
