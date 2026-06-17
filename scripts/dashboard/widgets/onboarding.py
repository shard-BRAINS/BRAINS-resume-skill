"""The resume-first onboarding surface.

Rendered on the Home tab whenever the active candidate's intent has not
been collected. Shows resume context and a short clarifying form; on submit
it writes the career-intent fields (which stamps intent_collected_at), and
the surface stops appearing.
"""
import streamlit as st

from scripts.tracker.candidates import update_candidate_intent
from scripts.tracker.db import open_db


CAREER_STAGES = (
    "student", "first_job", "early", "mid", "senior", "executive",
    "returning", "career_changer",
)
DIRECTIONS = ("grow", "leadership", "pivot", "first_role", "re_enter")
LEADERSHIP_INTENT = ("yes", "no", "maybe")
TIMELINES = ("actively_applying", "exploring", "passive")
WORK_PREFERENCES = (
    "remote", "hybrid", "onsite", "full_time", "part_time", "casual",
)


def onboarding_needed(candidate) -> bool:
    """True when the candidate has not completed the intent form yet."""
    return candidate.intent_collected_at is None


def resume_context(candidate_id: int) -> dict:
    """Return {has_resume, count, latest_template, latest_created_at} for the
    candidate's non-archived resumes — the 'resume-informed' context."""
    conn = open_db()
    try:
        rows = conn.execute(
            "SELECT template, created_at FROM resume_versions "
            "WHERE candidate_id=? AND archived_at IS NULL "
            "ORDER BY created_at DESC",
            (candidate_id,),
        ).fetchall()
    finally:
        conn.close()
    if not rows:
        return {"has_resume": False, "count": 0,
                "latest_template": None, "latest_created_at": None}
    return {
        "has_resume": True,
        "count": len(rows),
        "latest_template": rows[0][0],
        "latest_created_at": rows[0][1],
    }


def render_onboarding(candidate) -> None:
    """Render the onboarding surface for a candidate whose intent is unset."""
    with st.container(border=True):
        st.markdown(f"### Finish setting up {candidate.first_name}'s profile")
        ctx = resume_context(candidate.id)
        if ctx["has_resume"]:
            st.caption(
                f"Resume on file: {ctx['count']} version(s), latest is a "
                f"'{ctx['latest_template']}' template. Answer a few questions "
                "below so playbooks and JD matching are tailored."
            )
        else:
            st.caption(
                "No resume on file yet — start the **Build a base resume** "
                "playbook above, or load one via the Resumes tab. You can "
                "also answer these questions now."
            )

        career_stage = st.selectbox(
            "Career stage", CAREER_STAGES, key="ob_career_stage")
        direction = st.selectbox(
            "Direction", DIRECTIONS, key="ob_direction")
        target_roles_raw = st.text_input(
            "Target roles (comma-separated)", key="ob_target_roles")
        target_industries_raw = st.text_input(
            "Target industries (comma-separated)", key="ob_target_industries")
        leadership_intent = st.radio(
            "Seeking a leadership / people-management role?",
            LEADERSHIP_INTENT, horizontal=True, key="ob_leadership")
        work_preferences = st.multiselect(
            "Work preferences", WORK_PREFERENCES, key="ob_work_prefs")
        location = st.text_input("Location", key="ob_location")
        relocation_open = st.checkbox(
            "Open to relocating", key="ob_relocation")
        role_priorities = st.text_area(
            "What matters to you in a role? (optional)", key="ob_priorities")
        timeline = st.selectbox(
            "Timeline", TIMELINES, key="ob_timeline")

        if st.button("Save & finish setup", key="ob_save"):
            update_candidate_intent(
                candidate.id,
                career_stage=career_stage,
                direction=direction,
                target_roles=[r.strip() for r in target_roles_raw.split(",")
                              if r.strip()],
                target_industries=[r.strip() for r in
                                   target_industries_raw.split(",")
                                   if r.strip()],
                leadership_intent=leadership_intent,
                work_preferences=work_preferences,
                location=location or None,
                relocation_open=1 if relocation_open else 0,
                role_priorities=role_priorities or None,
                timeline=timeline,
            )
            st.success("Profile complete. The dashboard is yours.")
            st.rerun()
