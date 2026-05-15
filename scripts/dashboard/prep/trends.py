"""Weekly/rolling aggregation helpers for the Overview tab tiles.

Each function takes a list of ApplicationRow objects and a `now` timestamp,
returns a scalar count. Pure — no Streamlit imports, no I/O.
"""
from datetime import datetime, timedelta
from typing import List


INTERVIEW_EVENT_TYPES = {"phone_screen", "first_round", "second_round", "take_home"}


def _row_submitted_within(row, days: int, now: datetime) -> bool:
    submitted_str = getattr(row, "submitted_at", "")
    if not submitted_str:
        return False
    try:
        submitted = datetime.fromisoformat(submitted_str)
    except (ValueError, TypeError):
        return False
    return submitted >= now - timedelta(days=days)


def applications_this_week_count(rows: List, now: datetime = None) -> int:
    """Count rows submitted in the last 7 days."""
    if now is None:
        now = datetime.now()
    return sum(1 for r in rows if _row_submitted_within(r, 7, now))


def callback_count_last_n_days(rows: List, days: int = 30, now: datetime = None) -> int:
    """Count rows submitted in the last N days with latest_outcome == 'callback'."""
    if now is None:
        now = datetime.now()
    return sum(
        1 for r in rows
        if _row_submitted_within(r, days, now)
        and getattr(r, "latest_outcome", None) == "callback"
    )


def interview_count_last_n_days(rows: List, days: int = 30, now: datetime = None) -> int:
    """Count rows in the last N days whose latest_outcome is an interview event."""
    if now is None:
        now = datetime.now()
    return sum(
        1 for r in rows
        if _row_submitted_within(r, days, now)
        and getattr(r, "latest_outcome", None) in INTERVIEW_EVENT_TYPES
    )
