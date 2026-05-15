"""Idle-state callout detection for the Overview tab.

When the user has no current activity to report, surface a positive callout
rather than an empty void. Three callout types:

  1. "No applications submitted this week" — when 0 applications in last 7 days
  2. "No pending outcomes — every application has been responded to" — when
     every non-archived application has a terminal outcome
  3. (Future) "AI-signal score consistently low" — would require resume-version
     scoring across history; deferred until Overview tab can pass that data in

Returns a list of strings; render order is the order of this list.
"""
from datetime import datetime, timedelta
from typing import List


TERMINAL_OUTCOMES = {"offer", "rejection", "withdrew", "ghosted"}


def _row_submitted_within(row, days: int, now: datetime) -> bool:
    submitted_str = getattr(row, "submitted_at", "")
    if not submitted_str:
        return False
    try:
        submitted = datetime.fromisoformat(submitted_str)
    except (ValueError, TypeError):
        return False
    return submitted >= now - timedelta(days=days)


def detect_idle_states(rows: List, now: datetime = None) -> List[str]:
    """Return callout strings for whichever idle states currently apply."""
    if now is None:
        now = datetime.now()
    callouts: List[str] = []

    # Callout 1: no applications this week
    if not any(_row_submitted_within(r, 7, now) for r in rows):
        callouts.append(
            "No applications submitted this week — sensory-bandwidth respected."
        )

    # Callout 2: no pending outcomes
    if rows:
        all_terminal = all(
            getattr(r, "latest_outcome", None) in TERMINAL_OUTCOMES
            for r in rows
        )
        if all_terminal:
            callouts.append(
                "No pending outcomes — every application has been responded to."
            )

    return callouts
