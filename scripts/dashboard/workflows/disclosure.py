"""/brains-disclosure — record outcomes from the disclosure-decision framework.

The *conversation* still happens in Claude Code (the brains-disclosure skill
walks the six factors and produces a landed strength). This surface is where
the outcome is recorded against the candidate, where the worksheet PDF is
generated, and where the history of past sessions is visible.

The plan: keep coaching in CC where the LLM is strongest at the back-and-forth;
keep persistence + downstream auto-apply in the dashboard where the data layer
lives. See docs/plans/2026-06-08-disclosure-framework-polish.md.
"""
from __future__ import annotations

from pathlib import Path
from typing import Mapping, Optional

import streamlit as st

from scripts.dashboard.workflows._card import handoff_button
from scripts.tracker.candidates import get_active_candidate
from scripts.tracker.models import DISCLOSURE_STRENGTHS


# ---------------------------------------------------------------------------
# Pure helpers (no Streamlit) — unit-testable
# ---------------------------------------------------------------------------

FACTOR_QUESTIONS = (
    ("factor_1", "Is the employer ND-affirming in concrete, formal-programme terms (not just marketing copy)?"),
    ("factor_2", "Is the role itself disability-, accessibility-, or ND-affirming-adjacent?"),
    ("factor_3", "Are you applying through a channel that already screens for ND inclusion?"),
    ("factor_4", "Do you need an accommodation at the application stage itself?"),
    ("factor_5", "Are you values-driven to disclose regardless of bias risk?"),
    ("factor_6", "Has an employment advocate or disability-rights lawyer advised disclosure in your specific case?"),
)

_STRENGTH_LABELS = {
    "non-disclosure": "Non-disclosure",
    "neutral": "Neutral signalling",
    "explicit": "Explicit disclosure",
    "undecided": "Undecided",
}


def _is_strong_yes(answer: Optional[str]) -> bool:
    """A factor answer counts as strong-yes when it starts with 'yes'.

    Catches the realistic answer shapes:
      - "Yes"
      - "Yes — formal programme verified"
      - "yes, conditional on employer"
    Does not catch "no", "conditional no", "unsure", "n/a".
    """
    if not answer:
        return False
    return answer.strip().lower().startswith("yes")


def suggest_strength(factors: Mapping[str, Optional[str]]) -> str:
    """Suggest a disclosure strength from the six factor answers.

    Algorithm (mirrors the framework's structural-alignment logic):

      - Count strong-yes answers across factors 1, 2, 3, 5.
        * 0 or 1 → non-disclosure (default holds)
        * 2     → neutral
        * 3 or 4 → explicit
      - Factor 4 (accommodation needed at application stage) bumps the
        suggestion up one step — participation requires some disclosure.
      - Factor 6 (professional advice given) is informational; the
        algorithm doesn't have the content of the advice, so it doesn't
        change the suggestion.

    The suggestion is exactly that — a suggestion. The dashboard always
    lets the user override it before saving.
    """
    structural = sum(
        _is_strong_yes(factors.get(k))
        for k in ("factor_1", "factor_2", "factor_3", "factor_5")
    )
    if structural <= 1:
        base = "non-disclosure"
    elif structural == 2:
        base = "neutral"
    else:
        base = "explicit"

    if _is_strong_yes(factors.get("factor_4")):
        bump = {
            "non-disclosure": "neutral",
            "neutral": "explicit",
            "explicit": "explicit",
        }
        return bump[base]
    return base


def _format_strength_label(strength: str) -> str:
    return _STRENGTH_LABELS.get(strength, strength)


# ---------------------------------------------------------------------------
# Streamlit surface
# ---------------------------------------------------------------------------

def render(file_path: Optional[Path] = None, key_prefix: str = "disclosure") -> None:
    st.markdown("**Walk through the disclosure-decision framework.**")
    st.caption(
        "Whether, when, and how to disclose neurodivergence. Always your call "
        "— this is structured reflection, not a prescription."
    )

    _render_safeguarding()

    active = get_active_candidate()
    if active is None:
        st.error("No active candidate. Select or create one in the sidebar.")
        return

    st.markdown("---")
    _render_coaching_handoff(key_prefix)

    st.markdown("---")
    _render_record_form(active, key_prefix)

    st.markdown("---")
    _render_history(active.id, key_prefix)


def _render_safeguarding() -> None:
    st.info(
        "**This is general guidance, not legal or medical advice.** For "
        "specific decisions about your application, accommodation, or "
        "disclosure, consult an employment advocate, disability-rights "
        "lawyer, or — where relevant — a clinician.\n\n"
        "**Default position:** the framework starts from *not* disclosing "
        "neurodivergent identity on the resume itself. The six factors "
        "below may shift that default — but the decision is always yours."
    )


def _render_coaching_handoff(key_prefix: str) -> None:
    st.markdown("### Run the coaching turn in Claude Code")
    st.caption(
        "The full six-factor walkthrough lives in the brains-disclosure skill. "
        "Use the form below to record the outcome once you've worked through it."
    )
    handoff_button(
        "disclosure", [],
        note="Walks the six framework factors, suggests a strength, offers a worksheet.",
        key=f"{key_prefix}_handoff_btn",
    )


def _render_record_form(active, key_prefix: str) -> None:
    from scripts.tracker import disclosure as disclosure_db

    st.markdown("### Record a disclosure session")
    st.caption(
        f"Logging against **{active.first_name} {active.last_name}**. "
        "Recorded sessions feed downstream workflows (tailor, review, "
        "cover-letter) so they respect your landed preference."
    )

    target_employer = st.text_input(
        "Target employer (optional)",
        key=f"{key_prefix}_employer",
    )
    target_role = st.text_input(
        "Target role (optional)",
        key=f"{key_prefix}_role",
    )

    factor_values: dict[str, str] = {}
    with st.expander("Six-factor answers", expanded=True):
        for field, question in FACTOR_QUESTIONS:
            factor_values[field] = st.text_area(
                question,
                key=f"{key_prefix}_{field}",
                height=68,
            )

    suggested = suggest_strength(factor_values)
    st.markdown(
        f"**Framework suggestion:** {_format_strength_label(suggested)} "
        "— this is a suggestion, not a decision. Override below."
    )

    landed = st.selectbox(
        "Landed disclosure strength",
        options=list(DISCLOSURE_STRENGTHS),
        index=list(DISCLOSURE_STRENGTHS).index(suggested),
        format_func=_format_strength_label,
        key=f"{key_prefix}_landed",
    )

    notes = st.text_area(
        "Notes (optional — reasoning, caveats, employer context)",
        key=f"{key_prefix}_notes",
        height=80,
    )

    col_save, col_save_and_gen = st.columns(2)

    with col_save:
        if st.button("Save session", key=f"{key_prefix}_save_btn"):
            session_id = disclosure_db.create_session(
                candidate_id=active.id,
                landed_strength=landed,
                target_employer=target_employer or None,
                target_role=target_role or None,
                factor_1=factor_values.get("factor_1") or None,
                factor_2=factor_values.get("factor_2") or None,
                factor_3=factor_values.get("factor_3") or None,
                factor_4=factor_values.get("factor_4") or None,
                factor_5=factor_values.get("factor_5") or None,
                factor_6=factor_values.get("factor_6") or None,
                notes=notes or None,
            )
            st.success(
                f"Recorded session #{session_id} — landed strength: "
                f"{_format_strength_label(landed)}."
            )

    with col_save_and_gen:
        if st.button("Save + generate worksheet", key=f"{key_prefix}_save_gen_btn"):
            from scripts.generators.disclosure_worksheet import generate
            session_id = disclosure_db.create_session(
                candidate_id=active.id,
                landed_strength=landed,
                target_employer=target_employer or None,
                target_role=target_role or None,
                factor_1=factor_values.get("factor_1") or None,
                factor_2=factor_values.get("factor_2") or None,
                factor_3=factor_values.get("factor_3") or None,
                factor_4=factor_values.get("factor_4") or None,
                factor_5=factor_values.get("factor_5") or None,
                factor_6=factor_values.get("factor_6") or None,
                notes=notes or None,
            )
            try:
                md_path, pdf_path = generate(session_id)
            except Exception as exc:
                st.error(f"Session saved but worksheet generation failed: {exc}")
                return
            st.success(
                f"Recorded session #{session_id} and wrote worksheet to "
                f"`{pdf_path}`."
            )
            try:
                with open(pdf_path, "rb") as fh:
                    st.download_button(
                        "Download worksheet PDF",
                        data=fh.read(),
                        file_name=pdf_path.name,
                        mime="application/pdf",
                        key=f"{key_prefix}_pdf_dl",
                    )
            except OSError:
                pass


def _render_history(candidate_id: int, key_prefix: str) -> None:
    from scripts.tracker import disclosure as disclosure_db

    st.markdown("### Past sessions")
    sessions = disclosure_db.list_sessions_for_candidate(candidate_id)
    if not sessions:
        st.caption("No disclosure sessions recorded yet for this candidate.")
        return

    for s in sessions:
        date_str = s.created_at[:10] if s.created_at else "?"
        target_bits = " · ".join(
            bit for bit in (s.target_employer, s.target_role) if bit
        )
        header = f"**{date_str}** — {_format_strength_label(s.landed_strength)}"
        if target_bits:
            header += f"  ({target_bits})"
        with st.expander(header):
            for field, question in FACTOR_QUESTIONS:
                value = getattr(s, field, None)
                if value:
                    st.markdown(f"- *{question}*\n  - {value}")
            if s.notes:
                st.markdown(f"**Notes:** {s.notes}")
            if s.artifact_uid:
                st.caption(f"Worksheet artifact UID: `{s.artifact_uid}`")
            else:
                st.caption("No worksheet generated for this session.")
            if st.button(
                "Archive this session",
                key=f"{key_prefix}_archive_{s.id}",
            ):
                disclosure_db.archive_session(s.id)
                st.success(f"Archived session #{s.id}.")
                st.rerun()
