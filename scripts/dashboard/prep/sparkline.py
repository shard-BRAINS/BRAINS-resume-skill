"""Sparkline-data preparation for the Overview tab.

Three sparkline cards on Overview:
  - AI-signal trend over last 30 days (not in this module — requires resume
    versions + ai_signal_check; computed separately at Overview render time)
  - Applications per week, last 8 weeks
  - Callback rate rolling 30-day, last 90 days

These functions are pure — they take ApplicationRow lists in and return
chart-ready dicts/lists out. No Streamlit imports.
"""
from datetime import date, datetime, timedelta
from typing import List


def applications_per_week_8w(rows: List, now: datetime = None) -> List[dict]:
    """Bucket rows by week for the last 8 weeks.

    Returns a list of 8 dicts: [{week_starting: "YYYY-MM-DD", count: N}, ...]
    Order: oldest week first, most recent week last (for chart left-to-right).
    """
    if now is None:
        now = datetime.now()
    # Find the Monday of the current week
    today = now.date()
    days_since_monday = today.weekday()
    this_monday = today - timedelta(days=days_since_monday)
    # 8 weeks back from the current Monday
    weeks = [
        this_monday - timedelta(days=7 * (7 - i))
        for i in range(8)
    ]
    # Initialise counts
    by_week = {w.isoformat(): 0 for w in weeks}
    for r in rows:
        submitted_str = getattr(r, "submitted_at", "")
        if not submitted_str:
            continue
        try:
            submitted = datetime.fromisoformat(submitted_str).date()
        except (ValueError, TypeError):
            continue
        # Which Monday-week does this row belong to?
        row_monday = submitted - timedelta(days=submitted.weekday())
        key = row_monday.isoformat()
        if key in by_week:
            by_week[key] += 1
    return [{"week_starting": w.isoformat(), "count": by_week[w.isoformat()]} for w in weeks]


def callback_rate_rolling_30d(rows: List, now: datetime = None) -> List[dict]:
    """Rolling 30-day callback rate over the last 90 days.

    For each day in the last 90: rate = (callbacks in prior 30d) / (apps in prior 30d).
    Returns [] if no applications in the 90-day window.
    """
    if now is None:
        now = datetime.now()
    today = now.date()
    window_start = today - timedelta(days=90)

    # Gather rows in the 120-day window (so 30d-prior at window_start works)
    extended_window_start = window_start - timedelta(days=30)
    relevant = []
    for r in rows:
        submitted_str = getattr(r, "submitted_at", "")
        if not submitted_str:
            continue
        try:
            submitted = datetime.fromisoformat(submitted_str).date()
        except (ValueError, TypeError):
            continue
        if submitted >= extended_window_start:
            relevant.append((submitted, getattr(r, "latest_outcome", None)))

    if not relevant:
        return []

    series = []
    for i in range(90):
        day = window_start + timedelta(days=i)
        prior_30_start = day - timedelta(days=30)
        apps = [s for s, _ in relevant if prior_30_start <= s < day]
        if not apps:
            continue
        callbacks = sum(1 for s, o in relevant if prior_30_start <= s < day and o == "callback")
        rate = callbacks / len(apps)
        series.append({"date": day.isoformat(), "rate": rate})
    return series
