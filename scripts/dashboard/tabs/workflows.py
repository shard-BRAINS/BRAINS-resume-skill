"""Workflows tab — all 15 slash commands as cards, grouped by theme."""
from __future__ import annotations

import streamlit as st

from scripts.dashboard.style import INCUBATOR_BLUE
from scripts.dashboard.workflows import (
    career_change,
    cover_letter,
    create,
    disclosure,
    edit,
    linkedin,
    linkedin_improve,
    precheck,
    tailor,
)


def _import_phase3():
    """Lazy-import Phase 3 modules so this tab loads cleanly even when they don't exist yet."""
    from scripts.dashboard.workflows import check, consolidate, deai, jd_analyze, review, track
    return {
        "check": check,
        "consolidate": consolidate,
        "deai": deai,
        "jd_analyze": jd_analyze,
        "review": review,
        "track": track,
    }


def _render_card(col, slug: str, icon: str, label: str, blurb: str, module=None) -> None:
    """Render a single workflow card in the given Streamlit column."""
    with col:
        st.markdown(
            f"<div style='border:1px solid {INCUBATOR_BLUE}33; border-radius:8px; padding:12px; margin-bottom:8px;'>"
            f"<div style='font-size:1.6em;'>{icon}</div>"
            f"<div style='font-weight:600; color:{INCUBATOR_BLUE};'>{label}</div>"
            f"<div style='font-size:0.85em; color:#888;'>{blurb}</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        with st.expander(f"Open {label}"):
            if module is not None:
                module.render(file_path=None, key_prefix=f"wftab_{slug.replace('-', '_')}")
            else:
                st.info(f"`{slug}` will be available after Phase 3 lands.")


def render() -> None:
    st.header("Workflows")
    st.caption("Run any BRAINS workflow from here. Validator-backed ones execute in-dashboard; LLM-heavy ones copy the slash command to your clipboard for Claude Code.")

    phase3 = {}
    try:
        phase3 = _import_phase3()
    except Exception:
        phase3 = {}

    st.subheader("1 · Pre-application & decisions")
    cols = st.columns(3)
    _render_card(cols[0], "precheck",      "🛡️", "Pre-application","Six-question coaching pass before submit", precheck)
    _render_card(cols[1], "jd-analyze",    "📋", "JD analyze",     "Red flags, masking cost, role-fit", phase3.get("jd_analyze"))
    _render_card(cols[2], "disclosure",    "💭", "Disclosure",     "Walk through disclosure decision", disclosure)

    st.subheader("2 · Resume & cover docs")
    cols = st.columns(3)
    _render_card(cols[0], "create",        "🆕", "Create",         "Build a resume from scratch", create)
    _render_card(cols[1], "review",        "🔍", "Review",         "Audit a resume for ND-bias, ATS, and integrity", phase3.get("review"))
    _render_card(cols[2], "tailor",        "🎯", "Tailor",         "Customise a resume to a specific JD", tailor)
    cols = st.columns(3)
    _render_card(cols[0], "edit",          "✏️", "Edit",           "Apply review fixes to a resume", edit)
    _render_card(cols[1], "career-change", "🔄", "Career change",  "Translate experience for a pivot", career_change)
    _render_card(cols[2], "deai",          "🧹", "De-AI",          "Scan + suggest de-AI rewrites", phase3.get("deai"))
    cols = st.columns(3)
    _render_card(cols[0], "cover-letter",  "💌", "Cover letter",   "Generate a cover letter for a JD", cover_letter)
    _render_card(cols[1], "check",         "✅", "Final check",    "ATS + integrity + bias + AI-signal composite", phase3.get("check"))

    st.subheader("3 · Track & LinkedIn")
    cols = st.columns(3)
    _render_card(cols[0], "track",            "📈", "Track",           "Manage application outcomes", phase3.get("track"))
    _render_card(cols[1], "linkedin",         "📥", "LinkedIn ingest", "Import a LinkedIn export ZIP", linkedin)
    _render_card(cols[2], "linkedin-improve", "💼", "LinkedIn improve","Rewrite Headline / About / etc.", linkedin_improve)
    cols = st.columns(3)
    _render_card(cols[0], "consolidate",      "🧩", "Consolidate",     "Resolve resume ↔ LinkedIn inconsistencies", phase3.get("consolidate"))
