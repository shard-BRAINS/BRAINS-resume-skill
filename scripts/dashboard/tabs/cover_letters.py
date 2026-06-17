"""Cover Letters tab — table of cover letter versions linked to resumes + JDs."""
from pathlib import Path

import pandas as pd
import streamlit as st

from scripts.tracker.candidates import get_active_candidate
from scripts.tracker.db import open_db


def render() -> None:
    active = get_active_candidate()
    if active is None:
        st.info(
            "No active candidate. Select or create one in the sidebar to see "
            "cover letters."
        )
        return

    if st.button("↻ Refresh", key="cl_refresh"):
        st.rerun()

    rows = _list_cover_letters()

    if not rows:
        st.info(
            "No cover letters tracked yet. Run `/brains-cover-letter` and "
            "opt in to tracking at the end of the workflow."
        )
        return

    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "file_path": st.column_config.TextColumn("File", width="medium"),
            "template": st.column_config.TextColumn("Template", width="small"),
            "resume_version_id": st.column_config.NumberColumn("Resume", width="small"),
            "jd_company": st.column_config.TextColumn("Company", width="small"),
            "jd_role_title": st.column_config.TextColumn("Role", width="medium"),
            "ai_signal_score": st.column_config.NumberColumn(
                "AI-signal", help="Lower is better.", width="small",
            ),
            "created_at": st.column_config.TextColumn("Created", width="small"),
        },
        hide_index=True,
    )

    st.caption(f"Showing {len(df)} cover letters.")

    # Inline workflow actions (v1.4.0)
    st.markdown("---")
    st.subheader("Actions")
    rows = _list_cover_letters()
    if not rows:
        st.caption("_No cover letters tracked yet._")
        return

    from pathlib import Path as _P

    def _label(r: dict) -> str:
        fp = r.get("file_path") or "(no file)"
        filename = _P(fp).name if fp and fp != "(no file)" else "(no file)"
        company = r.get("jd_company", "") or ""
        role = r.get("jd_role_title", "") or ""
        return f"{filename} — {company} / {role}".strip(" —/")

    options = {_label(r): r["file_path"] for r in rows if r.get("file_path") and r["file_path"] != "(no file)"}
    if not options:
        st.caption("_No cover letters with a file path on disk yet._")
        return

    selected = st.selectbox("Select a cover letter to act on", options=list(options.keys()), key="cl_action_pick")
    if selected:
        from pathlib import Path
        from scripts.dashboard.workflows import deai as wf_deai, edit as wf_edit

        file_path = Path(options[selected])
        action = st.radio("Action", ["Edit", "De-AI"], horizontal=True, key="cl_action_radio")
        st.markdown("---")
        if action == "Edit":
            wf_edit.render(file_path=file_path, key_prefix="cltab_edit")
        elif action == "De-AI":
            wf_deai.render(file_path=file_path, key_prefix="cltab_deai")


def _list_cover_letters() -> list:
    """Read-only direct query for cover letters + computed AI-signal score.

    Scoped to the active candidate (Task 12). When no active candidate is set,
    returns an empty list.
    """
    from scripts.validators.ai_signal_check import ai_signal_check

    active = get_active_candidate()
    if active is None:
        return []

    conn = open_db()
    try:
        cur = conn.execute(
            """
            SELECT cl.id, cl.file_path, cl.template, cl.resume_version_id,
                   cl.jd_id, j.company, j.role_title, cl.created_at
            FROM cover_letters cl
            JOIN jds j ON j.id = cl.jd_id
            WHERE cl.archived_at IS NULL AND cl.candidate_id = ?
            ORDER BY cl.created_at DESC
            """,
            (active.id,),
        )
        rows = []
        for row in cur.fetchall():
            score = None
            if row[1] and Path(row[1]).exists():
                file_path = Path(row[1])
                if file_path.suffix == ".docx":
                    try:
                        from scripts.parsers.docx_to_text import parse_docx_resume
                        text = parse_docx_resume(file_path).get("raw_text", "")
                        if text:
                            score = ai_signal_check(text).score
                    except Exception:
                        score = None
            rows.append({
                "id": row[0],
                "file_path": row[1] or "(no file)",
                "template": row[2],
                "resume_version_id": row[3],
                "jd_company": row[5],
                "jd_role_title": row[6],
                "ai_signal_score": score,
                "created_at": row[7][:10] if row[7] else "",
            })
    finally:
        conn.close()
    return rows
