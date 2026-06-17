"""Data types for the playbook engine.

PlaybookStep / Playbook are immutable definitions (hardcoded in
definitions.py). PlaybookRun is a mutable DTO mapping 1:1 to a
playbook_runs row.
"""
from dataclasses import dataclass
from typing import Callable, Optional, Tuple


# Valid values for PlaybookStep.kind.
STEP_KINDS = ("in_dashboard", "handoff")

# Valid values for PlaybookRun.status.
RUN_STATUSES = ("active", "completed", "abandoned")


@dataclass(frozen=True)
class PlaybookStep:
    """One step in a playbook.

    kind:
      - 'in_dashboard': the dashboard runs this itself (a pure-Python
        validator). Completion is synchronous; no predicate.
      - 'handoff': LLM work handed off to Claude Code.

    command:   for handoff steps, the brains command (e.g. 'tailor').
    predicate: a callable (conn, run) -> bool that returns True once the
               step's output exists. None means the step has no auto-detect
               signal and advances by manual override only.
    """
    key: str
    label: str
    kind: str
    command: Optional[str] = None
    predicate: Optional[Callable] = None


@dataclass(frozen=True)
class Playbook:
    """An ordered sequence of steps assembled from existing commands."""
    key: str
    label: str
    steps: Tuple[PlaybookStep, ...]


@dataclass
class PlaybookRun:
    """A single run of a playbook — maps 1:1 to a playbook_runs row."""
    id: Optional[int]
    candidate_id: int
    playbook_key: str
    jd_id: Optional[int]
    current_step: int
    status: str
    created_at: str
    updated_at: str
    completed_at: Optional[str]
