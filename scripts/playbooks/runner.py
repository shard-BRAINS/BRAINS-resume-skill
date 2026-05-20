"""The playbook runner.

evaluate_run inspects a run's current step. If the step carries a completion
predicate and the predicate passes, the run advances — looping so that
several handoff steps completed between two dashboard renders all settle in
one call. It stops at the first step that is in_dashboard, manual-only, or
not yet complete. The manual override (runs.set_run_step) is always
available regardless.
"""
import sqlite3
from typing import Optional

from scripts.tracker.db import open_db
from scripts.playbooks.definitions import get_playbook
from scripts.playbooks.models import PlaybookRun
from scripts.playbooks.runs import get_run, advance_run


def evaluate_run(run_id: int) -> Optional[PlaybookRun]:
    """Auto-advance a run as far as its completion predicates allow.

    Returns the (possibly advanced) run, or None if the run does not exist.
    A predicate that raises sqlite3.Error is treated as 'not complete' so a
    bad predicate never crashes the caller.
    """
    run = get_run(run_id)
    if run is None or run.status != "active":
        return run

    while run.status == "active":
        playbook = get_playbook(run.playbook_key)
        if run.current_step >= len(playbook.steps):
            break
        step = playbook.steps[run.current_step]
        if step.predicate is None:
            break  # in_dashboard or manual-only — stop auto-advancing
        conn = open_db()
        try:
            try:
                done = bool(step.predicate(conn, run))
            except sqlite3.Error:
                done = False
        finally:
            conn.close()
        if not done:
            break
        run = advance_run(run.id)

    return run
