"""Resumes tab — table of resume versions with focus areas + AI-signal score.

Data source: SELECT * FROM resume_versions via a small helper in this file
that opens the tracker db directly. (The tracker.query module does not yet
expose a list_resume_versions helper; rather than adding one, we do a tight
read-only query here. Future refactor could promote it into tracker.query.)
"""
from pathlib import Path

import pandas as pd
import streamlit as st

from scripts.tracker.db import open_db


def render() -> None:
    if st.button("↻ Refresh", key="resumes_refresh"):
        st.rerun()

    rows = _list_resume_versions()

    if not rows:
        st.info(
            "No resume versions tracked yet. Run a workflow that opts in to "
            "tracking (e.g. `/brains-tailor` followed by registering the output)."
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
            "focus_areas": st.column_config.TextColumn("Focus Areas", width="medium"),
            "ai_signal_score": st.column_config.NumberColumn(
                "AI-signal", help="Lower is better. 0-9 clean, 30+ worth a rewrite.",
                width="small",
            ),
            "parent_id": st.column_config.NumberColumn("Parent", width="small"),
            "tagged_jd_id": st.column_config.NumberColumn("JD", width="small"),
            "created_at": st.column_config.TextColumn("Created", width="small"),
        },
        hide_index=True,
    )

    st.caption(f"Showing {len(df)} resume versions.")

    # Inline workflow actions (v1.4.0)
    st.markdown("---")
    st.subheader("Actions")
    versions = _list_resume_versions()
    if not versions:
        st.caption("_No resumes tracked yet._")
        return

    # Build labels: prefer filename + template + date
    def _label(v: dict) -> str:
        from pathlib import Path as _P
        fp = v.get("file_path") or "(no file)"
        filename = _P(fp).name if fp and fp != "(no file)" else "(no file)"
        return f"{filename} — {v.get('template', '')} — {v.get('created_at', '')}"

    options = {_label(v): v["file_path"] for v in versions if v.get("file_path") and v["file_path"] != "(no file)"}
    if not options:
        st.caption("_No resumes with a file path on disk yet._")
        return

    selected = st.selectbox("Select a resume to act on", options=list(options.keys()), key="resumes_action_pick")
    if selected:
        from pathlib import Path
        from scripts.dashboard.workflows import (
            check as wf_check,
            deai as wf_deai,
            edit as wf_edit,
            review as wf_review,
            tailor as wf_tailor,
        )

        file_path = Path(options[selected])
        action = st.radio(
            "Action",
            ["Review", "Edit", "Tailor", "De-AI", "Final check"],
            horizontal=True,
            key="resumes_action_radio",
        )
        st.markdown("---")
        if action == "Review":
            wf_review.render(file_path=file_path)
        elif action == "Edit":
            wf_edit.render(file_path=file_path)
        elif action == "Tailor":
            wf_tailor.render(file_path=file_path)
        elif action == "De-AI":
            wf_deai.render(file_path=file_path)
        elif action == "Final check":
            wf_check.render(file_path=file_path)


def _list_resume_versions() -> list:
    """Read-only direct query for resume versions + computed AI-signal score."""
    import json

    from scripts.validators.ai_signal_check import ai_signal_check

    conn = open_db()
    try:
        cur = conn.execute(
            """
            SELECT id, file_path, template, focus_areas, parent_id,
                   tagged_jd_id, created_at
            FROM resume_versions
            WHERE archived_at IS NULL
            ORDER BY created_at DESC
            """
        )
        rows = []
        for row in cur.fetchall():
            focus_areas_list = json.loads(row[3]) if row[3] else []
            # AI-signal score requires the resume text — for now we skip the
            # score column when file is absent. A future refactor could
            # extract text via docx_to_text / pdf_to_text. For v1.3.0, leave
            # ai_signal_score as None when text isn't available.
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
                "focus_areas": ", ".join(focus_areas_list),
                "ai_signal_score": score,
                "parent_id": row[4],
                "tagged_jd_id": row[5],
                "created_at": row[6][:10] if row[6] else "",
            })
    finally:
        conn.close()
    return rows
