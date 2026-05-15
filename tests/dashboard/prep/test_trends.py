"""Tests for scripts/dashboard/prep/trends.py — weekly aggregation helpers."""
from datetime import datetime, timedelta

from scripts.dashboard.prep.trends import (
    applications_this_week_count,
    callback_count_last_n_days,
    interview_count_last_n_days,
)


def _row(submitted_at=None, latest_outcome=None):
    class _Row:
        pass
    r = _Row()
    r.submitted_at = submitted_at.isoformat() if submitted_at and hasattr(submitted_at, "isoformat") else submitted_at
    r.latest_outcome = latest_outcome
    return r


def test_applications_this_week_zero_on_empty_input():
    now = datetime(2026, 5, 14)
    assert applications_this_week_count([], now=now) == 0


def test_applications_this_week_counts_rows_in_last_7_days():
    now = datetime(2026, 5, 14)
    rows = [
        _row(submitted_at=now - timedelta(days=1)),
        _row(submitted_at=now - timedelta(days=3)),
        _row(submitted_at=now - timedelta(days=10)),  # outside window
    ]
    assert applications_this_week_count(rows, now=now) == 2


def test_callback_count_last_30d():
    now = datetime(2026, 5, 14)
    rows = [
        _row(submitted_at=now - timedelta(days=5), latest_outcome="callback"),
        _row(submitted_at=now - timedelta(days=10), latest_outcome="callback"),
        _row(submitted_at=now - timedelta(days=15), latest_outcome="rejection"),
        _row(submitted_at=now - timedelta(days=40), latest_outcome="callback"),  # outside
    ]
    assert callback_count_last_n_days(rows, days=30, now=now) == 2


def test_interview_count_aggregates_interview_event_types():
    now = datetime(2026, 5, 14)
    rows = [
        _row(submitted_at=now - timedelta(days=5), latest_outcome="phone_screen"),
        _row(submitted_at=now - timedelta(days=5), latest_outcome="first_round"),
        _row(submitted_at=now - timedelta(days=5), latest_outcome="second_round"),
        _row(submitted_at=now - timedelta(days=5), latest_outcome="take_home"),
        _row(submitted_at=now - timedelta(days=5), latest_outcome="callback"),  # not interview
        _row(submitted_at=now - timedelta(days=5), latest_outcome="offer"),     # not interview
    ]
    assert interview_count_last_n_days(rows, days=30, now=now) == 4
