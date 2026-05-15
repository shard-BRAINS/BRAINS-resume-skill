"""Tests for scripts/dashboard/prep/sparkline.py — sparkline data preparation."""
from datetime import date, datetime, timedelta

from scripts.dashboard.prep.sparkline import (
    applications_per_week_8w,
    callback_rate_rolling_30d,
)


def _row(submitted_at, latest_outcome=None):
    class _Row:
        pass
    r = _Row()
    r.submitted_at = submitted_at.isoformat() if hasattr(submitted_at, "isoformat") else submitted_at
    r.latest_outcome = latest_outcome
    return r


def test_applications_per_week_empty_returns_8_zeros():
    data = applications_per_week_8w([], now=datetime(2026, 5, 14))
    assert len(data) == 8
    assert all(d["count"] == 0 for d in data)


def test_applications_per_week_distributes_by_week():
    now = datetime(2026, 5, 14)
    rows = [
        _row(now - timedelta(days=2)),   # this week
        _row(now - timedelta(days=8)),   # 1 week ago
        _row(now - timedelta(days=10)),  # 1-2 weeks ago
        _row(now - timedelta(days=60)),  # outside 8w window
    ]
    data = applications_per_week_8w(rows, now=now)
    counts = [d["count"] for d in data]
    # Most recent week should have the count-of-2-days-ago application
    assert counts[-1] >= 1


def test_applications_per_week_includes_week_starting_dates():
    data = applications_per_week_8w([], now=datetime(2026, 5, 14))
    for entry in data:
        assert "week_starting" in entry
        # Each week_starting should be 7 days apart
    for i in range(len(data) - 1):
        d1 = date.fromisoformat(data[i]["week_starting"])
        d2 = date.fromisoformat(data[i + 1]["week_starting"])
        assert (d2 - d1).days == 7


def test_callback_rate_empty_returns_empty_series():
    data = callback_rate_rolling_30d([], now=datetime(2026, 5, 14))
    assert data == []


def test_callback_rate_with_callbacks():
    now = datetime(2026, 5, 14)
    rows = [
        _row(now - timedelta(days=5), latest_outcome="callback"),
        _row(now - timedelta(days=10), latest_outcome="callback"),
        _row(now - timedelta(days=20)),  # no callback
        _row(now - timedelta(days=80)),  # outside window
    ]
    data = callback_rate_rolling_30d(rows, now=now)
    # Should produce a series of {date, rate} entries
    assert len(data) > 0
    for entry in data:
        assert "date" in entry
        assert "rate" in entry
        assert 0.0 <= entry["rate"] <= 1.0
