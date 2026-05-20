"""Drift tab — full-page deep dive.

Three pure data-builder helpers (testable without Streamlit) + render()
that composes them with Streamlit widgets.
"""
from __future__ import annotations

import json
from typing import Optional

from scripts.drift.lineage import get_candidate_lineage
from scripts.tracker.db import open_db


_CLASS_LABELS = {
    "identity": "Identity",
    "experience": "Experience",
    "education": "Education",
    "skills": "Skills",
    "certifications": "Certifications",
    "standalone_achievements": "Standalone achievements",
    "hobbies": "Hobbies",
    "languages": "Languages",
    "publications": "Publications",
    "portfolio_links": "Portfolio links",
}


def _lineage_data(scope: dict) -> dict:
    """Build the lineage strip data: nodes list + baseline_uid."""
    lineage = get_candidate_lineage(scope)
    nodes = [
        {
            "artifact_uid": v.artifact_uid,
            "created_at": v.created_at,
            "is_baseline": bool(
                _is_baseline_row(v.artifact_uid)
            ) if v.artifact_uid else False,
        }
        for v in lineage
    ]
    baseline_uid = next((n["artifact_uid"] for n in nodes if n["is_baseline"]), None)
    return {"nodes": nodes, "baseline_uid": baseline_uid}


def _is_baseline_row(artifact_uid: str) -> bool:
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT is_baseline FROM resume_versions WHERE artifact_uid=?",
            (artifact_uid,),
        ).fetchone()
    finally:
        conn.close()
    return bool(row and row[0])


def _load_scores(artifact_uid: str) -> tuple[Optional[dict], Optional[dict]]:
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT vs_parent_score, vs_baseline_score "
            "FROM resume_drift_scores WHERE artifact_uid=?",
            (artifact_uid,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None, None
    parent = json.loads(row[0]) if row[0] else None
    baseline = json.loads(row[1]) if row[1] else None
    return parent, baseline


def _selected_summary(artifact_uid: str) -> dict:
    """Build the 'Selected version summary' + per-class table."""
    vs_parent, vs_baseline = _load_scores(artifact_uid)
    per_class: dict = {}
    for cls in _CLASS_LABELS:
        per_class[cls] = {
            "label": _CLASS_LABELS[cls],
            "vs_parent_pct": (vs_parent or {}).get(cls, {}).get("pct"),
            "vs_baseline_pct": (vs_baseline or {}).get(cls, {}).get("pct"),
            "vs_parent_status": (vs_parent or {}).get(cls, {}).get("status"),
            "vs_baseline_status": (vs_baseline or {}).get(cls, {}).get("status"),
        }
    return {
        "artifact_uid": artifact_uid,
        "vs_parent_overall_pct": (vs_parent or {}).get("overall_pct"),
        "vs_baseline_overall_pct": (vs_baseline or {}).get("overall_pct"),
        "per_class_table": per_class,
    }


def _field_level_changes(artifact_uid: str) -> list[str]:
    """Flat list of field-level changes from both vs_parent and vs_baseline."""
    vs_parent, vs_baseline = _load_scores(artifact_uid)
    lines: list[str] = []
    for label, score in (("vs parent", vs_parent), ("vs baseline", vs_baseline)):
        if not score:
            continue
        for cls, info in score.items():
            if cls in ("overall_pct", "headline_changes"):
                continue
            if not isinstance(info, dict):
                continue
            for fc in info.get("field_changes", []) or []:
                lines.append(
                    f"{_CLASS_LABELS.get(cls, cls)} ({label}) · "
                    f"{fc.get('entry_id', '?')} · {fc['field']}: "
                    f"{fc.get('from')!r} → {fc.get('to')!r}"
                )
            for item in info.get("added", []) or []:
                lines.append(
                    f"{_CLASS_LABELS.get(cls, cls)} ({label}) · added: {item}"
                )
            for item in info.get("removed", []) or []:
                lines.append(
                    f"{_CLASS_LABELS.get(cls, cls)} ({label}) · removed: {item}"
                )
    # Dedupe while preserving order (vs_parent and vs_baseline may overlap).
    seen = set()
    out = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            out.append(line)
    return out


def render(scope: dict | None = None) -> None:
    import streamlit as st
    from scripts.drift.baseline import promote_baseline

    scope = scope or {"for_candidate": None}
    st.header("Drift")
    data = _lineage_data(scope)
    if not data["nodes"]:
        st.caption("No resumes for this candidate yet. Use /brains-import to upload a baseline.")
        return

    st.subheader(f"Drift · {scope.get('for_candidate') or 'profile holder'}")
    st.caption(f"Lineage: {len(data['nodes'])} versions · baseline {data['baseline_uid'] or '—'}")

    selected = st.selectbox(
        "Selected version",
        options=[n["artifact_uid"] for n in data["nodes"]],
        format_func=lambda u: f"{u} {'(baseline)' if u == data['baseline_uid'] else ''}",
        key="drift_selected_uid",
    )
    summary = _selected_summary(selected)
    vp = summary["vs_parent_overall_pct"]
    vb = summary["vs_baseline_overall_pct"]
    vp_txt = f"{vp:.1f}%" if vp is not None else "—"
    vb_txt = f"{vb:.1f}%" if vb is not None else "—"
    st.markdown(f"**vs parent:** {vp_txt}  ·  **vs baseline:** {vb_txt}")

    if selected != data["baseline_uid"]:
        with st.expander("Make this my baseline"):
            reason = st.text_input("Why? (required)", key="drift_promote_reason")
            if st.button("Promote", key="drift_promote_btn") and reason.strip():
                promote_baseline(selected, reason.strip())
                st.success(f"{selected} is now the active baseline. Drift scores have been recalculated.")
                st.rerun()

    st.markdown("#### Per-fact-class")
    import pandas as pd
    df = pd.DataFrame([
        {
            "Class": v["label"],
            "vs parent": (f"{v['vs_parent_pct']:.1f}%" if v["vs_parent_pct"] is not None else "—"),
            "vs baseline": (f"{v['vs_baseline_pct']:.1f}%" if v["vs_baseline_pct"] is not None else "—"),
        }
        for v in summary["per_class_table"].values()
    ])
    st.dataframe(df, use_container_width=True)

    st.markdown("#### Field-level changes")
    for line in _field_level_changes(selected):
        st.write(f"- {line}")
