"""Completion predicates for playbook handoff steps.

Each predicate is a pure read: (conn, run) -> bool. It returns True once the
step's output artifact exists in the tracker DB. The runner calls these to
decide whether to auto-advance a run.
"""
import sqlite3

from scripts.playbooks.models import PlaybookRun


def resume_tagged_to_jd(conn: sqlite3.Connection, run: PlaybookRun) -> bool:
    """True when a non-archived resume is tagged to the run's JD."""
    if run.jd_id is None:
        return False
    row = conn.execute(
        "SELECT 1 FROM resume_versions "
        "WHERE tagged_jd_id = ? AND archived_at IS NULL LIMIT 1",
        (run.jd_id,),
    ).fetchone()
    return row is not None


def cover_letter_for_jd(conn: sqlite3.Connection, run: PlaybookRun) -> bool:
    """True when a non-archived cover letter exists for the run's JD."""
    if run.jd_id is None:
        return False
    row = conn.execute(
        "SELECT 1 FROM cover_letters "
        "WHERE jd_id = ? AND archived_at IS NULL LIMIT 1",
        (run.jd_id,),
    ).fetchone()
    return row is not None


def application_for_jd(conn: sqlite3.Connection, run: PlaybookRun) -> bool:
    """True when an application has been registered for the run's JD."""
    if run.jd_id is None:
        return False
    row = conn.execute(
        "SELECT 1 FROM applications WHERE jd_id = ? LIMIT 1",
        (run.jd_id,),
    ).fetchone()
    return row is not None


def resume_created_after_run(conn: sqlite3.Connection, run: PlaybookRun) -> bool:
    """True when a non-archived resume for the candidate was created after
    the run started. Used by non-JD playbooks (e.g. build_resume) where the
    output is 'a new resume' rather than 'a resume tagged to a JD'."""
    row = conn.execute(
        "SELECT 1 FROM resume_versions "
        "WHERE candidate_id = ? AND archived_at IS NULL "
        "AND created_at > ? LIMIT 1",
        (run.candidate_id, run.created_at),
    ).fetchone()
    return row is not None
