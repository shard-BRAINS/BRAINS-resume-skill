"""Tests for scripts/dashboard/prep/idle_states.py — "no anomalies today" callout detection."""
from datetime import datetime, timedelta

from scripts.dashboard.prep.idle_states import (
    detect_idle_states,
)


def _row(submitted_at=None, latest_outcome=None):
    class _Row:
        pass
    r = _Row()
    r.submitted_at = submitted_at.isoformat() if submitted_at and hasattr(submitted_at, "isoformat") else submitted_at
    r.latest_outcome = latest_outcome
    return r


def test_no_applications_this_week_returns_callout():
    now = datetime(2026, 5, 14)
    # Old applications outside the 7d window
    rows = [_row(submitted_at=now - timedelta(days=30), latest_outcome="callback")]
    callouts = detect_idle_states(rows, now=now)
    assert any("No applications submitted this week" in c for c in callouts)


def test_applications_this_week_suppresses_no_applications_callout():
    now = datetime(2026, 5, 14)
    rows = [_row(submitted_at=now - timedelta(days=2))]
    callouts = detect_idle_states(rows, now=now)
    assert not any("No applications submitted this week" in c for c in callouts)


def test_all_terminal_outcomes_returns_no_pending_callout():
    now = datetime(2026, 5, 14)
    rows = [
        _row(submitted_at=now - timedelta(days=30), latest_outcome="offer"),
        _row(submitted_at=now - timedelta(days=30), latest_outcome="rejection"),
        _row(submitted_at=now - timedelta(days=30), latest_outcome="withdrew"),
    ]
    callouts = detect_idle_states(rows, now=now)
    assert any("No pending outcomes" in c for c in callouts)


def test_some_pending_outcomes_suppresses_no_pending_callout():
    now = datetime(2026, 5, 14)
    rows = [
        _row(submitted_at=now - timedelta(days=30), latest_outcome="offer"),
        _row(submitted_at=now - timedelta(days=10), latest_outcome=None),  # pending
    ]
    callouts = detect_idle_states(rows, now=now)
    assert not any("No pending outcomes" in c for c in callouts)


def test_empty_rows_returns_no_applications_callout():
    now = datetime(2026, 5, 14)
    callouts = detect_idle_states([], now=now)
    assert any("No applications submitted this week" in c for c in callouts)


def test_callouts_returned_as_list_of_strings():
    callouts = detect_idle_states([], now=datetime(2026, 5, 14))
    assert isinstance(callouts, list)
    for c in callouts:
        assert isinstance(c, str)
