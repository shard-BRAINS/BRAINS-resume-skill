"""The five hardcoded playbook definitions.

A playbook is an ordered list of steps assembled from existing brains
commands. Definitions are immutable; runtime progress lives in playbook_runs.

Step completion:
  - 'in_dashboard' steps run in the dashboard and complete synchronously
    (no predicate).
  - 'handoff' steps with a predicate auto-advance when the predicate passes.
  - 'handoff' steps without a predicate (e.g. a coaching conversation that
    leaves no artifact) advance by manual override only.
"""
from scripts.playbooks.models import Playbook, PlaybookStep
from scripts.playbooks import predicates as P


APPLY_TO_JOB = Playbook(
    key="apply_to_job",
    label="Apply to a job",
    steps=(
        PlaybookStep("analyze_jd", "Analyze the JD", "in_dashboard"),
        PlaybookStep("tailor_resume", "Tailor the resume", "handoff",
                     command="tailor", predicate=P.resume_tagged_to_jd),
        PlaybookStep("cover_letter", "Write the cover letter", "handoff",
                     command="cover-letter", predicate=P.cover_letter_for_jd),
        PlaybookStep("final_check", "Final pre-submit check", "in_dashboard"),
        PlaybookStep("precheck", "Pre-application coaching", "handoff",
                     command="precheck"),
        PlaybookStep("submit_track", "Submit & track", "handoff",
                     command="track", predicate=P.application_for_jd),
    ),
)

BUILD_RESUME = Playbook(
    key="build_resume",
    label="Build a base resume",
    steps=(
        PlaybookStep("create", "Interview & build", "handoff",
                     command="create", predicate=P.resume_created_after_run),
        PlaybookStep("review", "Review", "in_dashboard"),
        PlaybookStep("edit", "Apply edits", "handoff", command="edit"),
        PlaybookStep("final_check", "Final check", "in_dashboard"),
    ),
)

IMPROVE_RESUME = Playbook(
    key="improve_resume",
    label="Improve a resume",
    steps=(
        PlaybookStep("review", "Review", "in_dashboard"),
        PlaybookStep("edit", "Apply edits", "handoff", command="edit"),
        PlaybookStep("final_check", "Final check / de-AI", "in_dashboard"),
    ),
)

REFRESH_LINKEDIN = Playbook(
    key="refresh_linkedin",
    label="Refresh LinkedIn",
    steps=(
        PlaybookStep("ingest", "Ingest LinkedIn export", "handoff",
                     command="linkedin"),
        PlaybookStep("consolidate", "Consolidate vs resume", "handoff",
                     command="consolidate"),
        PlaybookStep("rewrite", "Rewrite the profile", "handoff",
                     command="linkedin-improve"),
    ),
)

CAREER_CHANGE = Playbook(
    key="career_change",
    label="Career change",
    steps=(
        PlaybookStep("translate", "Translate experience", "handoff",
                     command="career-change"),
    ),
)

ALL_PLAYBOOKS = (
    APPLY_TO_JOB, BUILD_RESUME, IMPROVE_RESUME, REFRESH_LINKEDIN, CAREER_CHANGE,
)

_BY_KEY = {pb.key: pb for pb in ALL_PLAYBOOKS}


def all_playbooks():
    """Return all five playbooks in display order."""
    return ALL_PLAYBOOKS


def get_playbook(key: str) -> Playbook:
    """Return the playbook with the given key. Raises KeyError if unknown."""
    if key not in _BY_KEY:
        raise KeyError(f"Unknown playbook: {key!r}")
    return _BY_KEY[key]
