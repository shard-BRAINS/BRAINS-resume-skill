"""/brains-jd-analyze — analyze a JD for ND-relevant signals + optional handoff."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st

from scripts.dashboard.workflows._card import handoff_button
from scripts.tracker.candidates import get_active_candidate
from scripts.validators.jd_analyzer import jd_analyze


def render(file_path: Optional[Path] = None, key_prefix: str = "jda") -> None:
    st.markdown("**Analyse a job description for ND-relevant signals.**")
    st.caption("Red flags, masking cost, role-fit score (vs your profile focus areas).")

    jd_text = st.text_area("Paste JD text", key=f"{key_prefix}_text", height=180, value="")
    jd_url = st.text_input("Or JD URL / file path (for the Claude Code handoff)", key=f"{key_prefix}_url")

    if st.button("Analyze", key=f"{key_prefix}_analyze_btn"):
        if not jd_text.strip():
            st.error("Paste the JD text first (in-dashboard analyzer needs raw text).")
        else:
            try:
                active = get_active_candidate()
                focus_areas = active.focus_areas if active else []
            except Exception:
                focus_areas = []
            try:
                result = jd_analyze(jd_text, focus_areas=focus_areas)
            except Exception as e:
                st.error(f"Analysis failed: {e}")
                return

            if result.role_fit_score is not None:
                st.metric("Role-fit score (vs your focus areas)", f"{result.role_fit_score}/100")

            findings = result.findings
            if not findings:
                st.success("No findings surfaced.")
            else:
                by_severity = {"high": [], "medium": [], "low": []}
                for f in findings:
                    sev = (f.severity or "low").lower()
                    by_severity.setdefault(sev, []).append(f)
                for sev in ("high", "medium", "low"):
                    items = by_severity.get(sev, [])
                    if items:
                        st.subheader(f"{sev.title()}-severity findings")
                        for f in items:
                            with st.expander(f"{f.code}"):
                                if f.excerpt:
                                    st.code(f.excerpt, language="text")
                                if f.suggestion:
                                    st.caption(f.suggestion)

            if result.required_list:
                st.markdown("**Required skills/competencies parsed:**")
                st.write(", ".join(result.required_list))
            if result.nice_list:
                st.markdown("**Nice-to-have skills/competencies:**")
                st.write(", ".join(result.nice_list))

    st.markdown("---")
    handoff_arg = jd_url or "(paste-from-clipboard)"
    handoff_button("jd-analyze", [handoff_arg], note="Full coaching report in Claude Code (will load the JD).", key=f"{key_prefix}_handoff_btn")


# ---------------------------------------------------------------------------
# Pure-Python persistence API (no Streamlit dependency)
# ---------------------------------------------------------------------------
import json  # noqa: E402 — placed here to keep Streamlit imports grouped above

from scripts.tracker.add import add_jd
from scripts.outputs.io import ensure_jd_folder


def persist_analyzed_jd(
    raw_text: str,
    company: str,
    role_title: str,
    source: str,
    source_ref: Optional[str],
    analyzer_findings: dict,
    focus_areas_required: list[str],
    focus_areas_nice: list[str],
) -> tuple[int, Path]:
    """Persist the analyzed JD to tracker + outputs folder.

    Creates the per-JD folder, writes the raw JD as jd.txt, writes the
    analysis findings as jd-analysis.md, and returns the new jd_id and
    folder path. Called from the Streamlit "Save to tracker" button.
    """
    jd_id = add_jd(
        source=source,
        source_ref=source_ref,
        company=company,
        role_title=role_title,
        raw_text=raw_text,
        analyzer_findings=analyzer_findings,
        focus_areas_required=focus_areas_required,
        focus_areas_nice=focus_areas_nice,
    )
    folder = ensure_jd_folder(jd_id)
    (folder / "jd.txt").write_text(raw_text, encoding="utf-8")
    (folder / "jd-analysis.md").write_text(
        _findings_to_markdown(analyzer_findings, role_title, company),
        encoding="utf-8",
    )
    return jd_id, folder


def _findings_to_markdown(findings: dict, role: str, company: str) -> str:
    """Render analyzer findings as a Markdown report."""
    lines = [
        f"# JD analysis — {role} @ {company}",
        "",
        "```json",
        json.dumps(findings, indent=2),
        "```",
        "",
    ]
    return "\n".join(lines)
