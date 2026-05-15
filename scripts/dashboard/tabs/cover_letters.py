"""Cover Letters tab — table of cover letter versions linked to resumes + JDs."""
from pathlib import Path

import pandas as pd
import streamlit as st

from scripts.tracker.db import open_db


def render() -> None:
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


def _list_cover_letters() -> list:
    from scripts.validators.ai_signal_check import ai_signal_check

    conn = open_db()
    try:
        cur = conn.execute(
            """
            SELECT cl.id, cl.file_path, cl.template, cl.resume_version_id,
                   cl.jd_id, j.company, j.role_title, cl.created_at
            FROM cover_letters cl
            JOIN jds j ON j.id = cl.jd_id
            WHERE cl.archived_at IS NULL
            ORDER BY cl.created_at DESC
            """
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
