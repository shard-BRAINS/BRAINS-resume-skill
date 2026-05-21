"""The pipeline_mini widget — each JD as a card across five stages.

Stage of a JD, by which artifacts exist (latest-wins):
  application + terminal outcome      -> Outcome
  application                         -> Submitted
  cover letter                        -> Docs ready
  resume tagged to the JD             -> Tailoring
  nothing yet                         -> Lead
"""
import streamlit as st

from scripts.tracker.db import open_db


PIPELINE_STAGES = ("Lead", "Tailoring", "Docs ready", "Submitted", "Outcome")
_TERMINAL = ("offer", "rejection", "withdrew")


def classify_pipeline(candidate_id: int) -> dict:
    """Return {stage: [ {jd_id, company, role_title}, ... ]} for the
    candidate's non-archived JDs."""
    result: dict = {stage: [] for stage in PIPELINE_STAGES}
    conn = open_db()
    try:
        jds = conn.execute(
            "SELECT id, company, role_title FROM jds "
            "WHERE candidate_id=? AND archived_at IS NULL ORDER BY created_at ASC",
            (candidate_id,),
        ).fetchall()
        for jd_id, company, role_title in jds:
            card = {"jd_id": jd_id, "company": company, "role_title": role_title}
            app = conn.execute(
                "SELECT id FROM applications WHERE jd_id=? LIMIT 1", (jd_id,)
            ).fetchone()
            if app is not None:
                outcome = conn.execute(
                    "SELECT event_type FROM outcomes WHERE application_id=? "
                    "ORDER BY event_date DESC LIMIT 1",
                    (app[0],),
                ).fetchone()
                if outcome is not None and outcome[0] in _TERMINAL:
                    result["Outcome"].append(card)
                else:
                    result["Submitted"].append(card)
                continue
            has_cl = conn.execute(
                "SELECT 1 FROM cover_letters WHERE jd_id=? AND archived_at IS NULL "
                "LIMIT 1", (jd_id,)
            ).fetchone()
            if has_cl is not None:
                result["Docs ready"].append(card)
                continue
            has_resume = conn.execute(
                "SELECT 1 FROM resume_versions WHERE tagged_jd_id=? "
                "AND archived_at IS NULL LIMIT 1", (jd_id,)
            ).fetchone()
            if has_resume is not None:
                result["Tailoring"].append(card)
            else:
                result["Lead"].append(card)
    finally:
        conn.close()
    return result


def render_pipeline(candidate) -> None:
    """The pipeline_mini widget."""
    with st.container(border=True):
        st.markdown("**Pipeline**")
        board = classify_pipeline(candidate.id)
        cols = st.columns(len(PIPELINE_STAGES))
        for col, stage in zip(cols, PIPELINE_STAGES):
            with col:
                st.caption(f"{stage} ({len(board[stage])})")
                for card in board[stage][:5]:
                    st.markdown(f"- {card['company']}")
