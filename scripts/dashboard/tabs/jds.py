"""JDs tab — table of analyzed job descriptions with findings."""
import json

import pandas as pd
import streamlit as st

from scripts.tracker.db import open_db


def render() -> None:
    if st.button("↻ Refresh", key="jds_refresh"):
        st.rerun()

    rows = _list_jds()

    if not rows:
        st.info(
            "No JDs tracked yet. Run `/brains-jd-analyze` and opt in to "
            "saving the JD to the tracker at the end of the workflow."
        )
        return

    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "company": st.column_config.TextColumn("Company", width="medium"),
            "role_title": st.column_config.TextColumn("Role", width="medium"),
            "source": st.column_config.TextColumn("Source", width="small"),
            "finding_count": st.column_config.NumberColumn("Findings", width="small"),
            "role_fit_score": st.column_config.NumberColumn(
                "Fit",
                help="0-100. Higher is better. Computed against user's focus areas.",
                width="small",
            ),
            "created_at": st.column_config.TextColumn("Saved", width="small"),
        },
        hide_index=True,
    )

    selected_id = st.selectbox(
        "Show findings for JD:",
        options=[None] + [r["id"] for r in rows],
        format_func=lambda x: "(select a JD)" if x is None else f"#{x}",
    )
    if selected_id is not None:
        _render_findings_for_jd(selected_id, rows)


def _list_jds() -> list:
    conn = open_db()
    try:
        cur = conn.execute(
            """
            SELECT id, company, role_title, source,
                   analyzer_findings, created_at
            FROM jds
            WHERE archived_at IS NULL
            ORDER BY created_at DESC
            """
        )
        rows = []
        for row in cur.fetchall():
            findings = json.loads(row[4]) if row[4] else {}
            finding_count = (
                len(findings.get("findings", []))
                if isinstance(findings, dict) else 0
            )
            role_fit_score = (
                findings.get("role_fit_score")
                if isinstance(findings, dict) else None
            )
            rows.append({
                "id": row[0],
                "company": row[1],
                "role_title": row[2],
                "source": row[3],
                "finding_count": finding_count,
                "role_fit_score": role_fit_score,
                "created_at": row[5][:10] if row[5] else "",
                "_analyzer_findings": findings,
            })
    finally:
        conn.close()
    return rows


def _render_findings_for_jd(jd_id: int, rows: list) -> None:
    """Render the analyzer findings for the selected JD as an expander stack."""
    jd_row = next((r for r in rows if r["id"] == jd_id), None)
    if jd_row is None:
        return
    findings_dict = jd_row.get("_analyzer_findings", {})
    findings = findings_dict.get("findings", []) if isinstance(findings_dict, dict) else []

    st.markdown(f"### Findings for #{jd_id} — {jd_row['company']} / {jd_row['role_title']}")
    if not findings:
        st.caption("No structured findings recorded for this JD.")
        return

    for f in findings:
        with st.expander(f"**{f.get('code', 'finding')}** ({f.get('severity', '?')})"):
            st.write(f.get("suggestion", ""))
            if f.get("excerpt"):
                st.code(f["excerpt"], language=None)

    st.caption(
        "See `references/jd-analyzer.md` (workflow doc) for finding-code definitions."
    )
