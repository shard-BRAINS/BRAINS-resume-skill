"""Resumes tab — table of resume versions with focus areas + AI-signal score.

Data source: SELECT * FROM resume_versions via a small helper in this file
that opens the tracker db directly. (The tracker.query module does not yet
expose a list_resume_versions helper; rather than adding one, we do a tight
read-only query here. Future refactor could promote it into tracker.query.)
"""
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
            "resume versions."
        )
        return

    if st.button("↻ Refresh", key="resumes_refresh"):
        st.rerun()

    rows = _list_resume_versions()

    if not rows:
        st.info(
            "No resume versions tracked yet. Run a workflow that opts in to "
            "tracking (e.g. `/brains-tailor` followed by registering the output)."
        )
        return

    # Drift columns (v1.7.0): join per-resume drift scores by artifact_uid.
    # Drift surfaces scope by candidate_id (Task 15).
    drift_by_uid = {
        r["artifact_uid"]: r
        for r in _build_resume_rows({"candidate_id": active.id})
        if r.get("artifact_uid")
    }
    for row in rows:
        d = drift_by_uid.get(row.get("artifact_uid"))
        vp = d.get("drift_vs_parent") if d else None
        vb = d.get("drift_vs_baseline") if d else None
        row["drift_vs_parent"] = f"{vp:.1f}%" if vp is not None else "—"
        row["drift_vs_baseline"] = f"{vb:.1f}%" if vb is not None else "—"
        row["_drift_parent_changes"] = (
            "; ".join(d.get("headline_changes_vs_parent", [])) if d else ""
        )
        row["_drift_baseline_changes"] = (
            "; ".join(d.get("headline_changes_vs_baseline", [])) if d else ""
        )

    df = pd.DataFrame(rows)
    # Tooltip columns are data only — drop them from the visible frame.
    parent_help = "Set-shape % change vs the parent resume version."
    baseline_help = "Set-shape % change vs the active baseline resume."
    if "_drift_parent_changes" in df.columns:
        parent_changes = [c for c in df["_drift_parent_changes"] if c]
        if parent_changes:
            parent_help += " Headline changes: " + " | ".join(parent_changes[:3])
    if "_drift_baseline_changes" in df.columns:
        baseline_changes = [c for c in df["_drift_baseline_changes"] if c]
        if baseline_changes:
            baseline_help += " Headline changes: " + " | ".join(baseline_changes[:3])
    display_df = df.drop(
        columns=[c for c in ("artifact_uid", "_drift_parent_changes",
                             "_drift_baseline_changes") if c in df.columns]
    )
    st.dataframe(
        display_df,
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
            "drift_vs_parent": st.column_config.TextColumn(
                "Drift vs parent", help=parent_help, width="small",
            ),
            "drift_vs_baseline": st.column_config.TextColumn(
                "Drift vs baseline", help=baseline_help, width="small",
            ),
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
            wf_review.render(file_path=file_path, key_prefix="rsmtab_review")
        elif action == "Edit":
            wf_edit.render(file_path=file_path, key_prefix="rsmtab_edit")
        elif action == "Tailor":
            wf_tailor.render(file_path=file_path, key_prefix="rsmtab_tailor")
        elif action == "De-AI":
            wf_deai.render(file_path=file_path, key_prefix="rsmtab_deai")
        elif action == "Final check":
            wf_check.render(file_path=file_path, key_prefix="rsmtab_check")


def _list_resume_versions() -> list:
    """Read-only direct query for resume versions + computed AI-signal score.

    Scoped to the active candidate (Task 12). When no active candidate is set,
    returns an empty list.
    """
    import json

    from scripts.validators.ai_signal_check import ai_signal_check

    active = get_active_candidate()
    if active is None:
        return []

    conn = open_db()
    try:
        cur = conn.execute(
            """
            SELECT id, file_path, template, focus_areas, parent_id,
                   tagged_jd_id, created_at, artifact_uid
            FROM resume_versions
            WHERE archived_at IS NULL AND candidate_id = ?
            ORDER BY created_at DESC
            """,
            (active.id,),
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
                "artifact_uid": row[7],
            })
    finally:
        conn.close()
    return rows


def _build_resume_rows(scope: dict) -> list[dict]:
    """Build the per-resume row dicts for the Resumes-tab table.

    Pure helper (no Streamlit) so it can be unit-tested directly. Each row
    includes the existing fields (file, created, template, jd) plus the new
    drift columns:
      - drift_vs_parent: float | None — overall_pct from vs_parent_score
      - drift_vs_baseline: float | None — overall_pct from vs_baseline_score
      - headline_changes_vs_parent: list[str]
      - headline_changes_vs_baseline: list[str]
    """
    import json

    from scripts.drift.lineage import get_candidate_lineage

    lineage = get_candidate_lineage(scope)
    if not lineage:
        return []
    uids = [v.artifact_uid for v in lineage if v.artifact_uid]
    if not uids:
        return [_resume_to_row_dict(v, None, None) for v in lineage]

    placeholders = ",".join("?" * len(uids))
    conn = open_db()
    try:
        score_rows = conn.execute(
            f"SELECT artifact_uid, vs_parent_score, vs_baseline_score "
            f"FROM resume_drift_scores WHERE artifact_uid IN ({placeholders})",
            uids,
        ).fetchall()
    finally:
        conn.close()
    by_uid = {}
    for uid, vp, vb in score_rows:
        by_uid[uid] = {
            "vs_parent": json.loads(vp) if vp else None,
            "vs_baseline": json.loads(vb) if vb else None,
        }
    out = []
    for v in lineage:
        scores = by_uid.get(
            v.artifact_uid or "", {"vs_parent": None, "vs_baseline": None}
        )
        out.append(_resume_to_row_dict(
            v, scores.get("vs_parent"), scores.get("vs_baseline")
        ))
    return out


def _resume_to_row_dict(rv, vs_parent, vs_baseline) -> dict:
    """Map a ResumeVersion + (optional) scores into a row dict for the table."""
    return {
        "artifact_uid": rv.artifact_uid,
        "file_path": rv.file_path,
        "template": rv.template,
        "created_at": rv.created_at,
        "tagged_jd_id": rv.tagged_jd_id,
        "drift_vs_parent": (vs_parent or {}).get("overall_pct"),
        "drift_vs_baseline": (vs_baseline or {}).get("overall_pct"),
        "headline_changes_vs_parent": (vs_parent or {}).get("headline_changes", []),
        "headline_changes_vs_baseline": (vs_baseline or {}).get("headline_changes", []),
    }
