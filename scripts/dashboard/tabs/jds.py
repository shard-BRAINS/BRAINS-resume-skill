"""JDs tab — table of analyzed job descriptions with findings."""
import pandas as pd
import streamlit as st

from scripts.tracker.candidates import get_active_candidate


def render() -> None:
    active = get_active_candidate()
    if active is None:
        st.info(
            "No active candidate. Select or create one in the sidebar to see JDs."
        )
        return

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

    # Inline workflow actions (v1.4.0)
    st.markdown("---")
    st.subheader("Actions")
    rows = _list_jds()
    if not rows:
        st.caption("_No JDs tracked yet._")
        return

    def _label(r: dict) -> str:
        company = r.get("company", "") or ""
        role = r.get("role_title", "") or ""
        return f"{company} / {role}".strip(" /")

    options = {_label(r): r.get("source", "") for r in rows if r.get("company") or r.get("role_title")}
    if not options:
        st.caption("_No JDs with a company/role label._")
        return

    selected = st.selectbox("Select a JD to act on", options=list(options.keys()), key="jds_action_pick")
    if selected:
        from scripts.dashboard.workflows import jd_analyze as wf_jda, tailor as wf_tailor

        jd_source = options[selected]
        action = st.radio(
            "Action",
            ["Analyze", "Tailor a resume to this JD"],
            horizontal=True,
            key="jds_action_radio",
        )
        st.markdown("---")
        if action == "Analyze":
            wf_jda.render(file_path=None, key_prefix="jdtab_jda")
            if jd_source:
                st.caption(f"JD source: `{jd_source}` — paste its text into the analyzer above, or use the handoff button.")
        elif action == "Tailor a resume to this JD":
            wf_tailor.render(file_path=None, key_prefix="jdtab_tailor")
            if jd_source:
                st.caption(f"JD source: `{jd_source}`")


def _list_jds() -> list:
    """Return JD row dicts for the active candidate.

    Routes through scripts.tracker.query.list_jds, which auto-scopes to the
    active candidate (Task 7).
    """
    from scripts.tracker.query import list_jds

    rows = []
    for jd in list_jds():
        findings = jd.analyzer_findings if isinstance(jd.analyzer_findings, dict) else {}
        finding_count = len(findings.get("findings", []))
        role_fit_score = findings.get("role_fit_score")
        rows.append({
            "id": jd.id,
            "company": jd.company,
            "role_title": jd.role_title,
            "source": jd.source,
            "finding_count": finding_count,
            "role_fit_score": role_fit_score,
            "created_at": jd.created_at[:10] if jd.created_at else "",
            "_analyzer_findings": findings,
        })
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
