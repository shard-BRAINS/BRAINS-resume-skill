"""Cached query wrappers for the dashboard.

Each function wraps a corresponding function in scripts.tracker.query with
@st.cache_data(ttl=60). Tabs import from here, never directly from
scripts.tracker.query. Manual refresh per tab calls .clear() on the matching
wrapper; clear_all_caches() flushes everything (used by the sidebar global
refresh button).

Profile reads/writes are NOT cached — they go directly through
scripts.tracker.profile because the values are rarely-changed and freshness
matters more than cache hit rate.
"""
from datetime import datetime
from typing import List, Optional

import streamlit as st

from scripts.tracker import query as _query
from scripts.tracker.models import EfficacyRow, WeeklySummary
from scripts.tracker.query import ApplicationRow


@st.cache_data(ttl=60)
def cached_list_applications(
    company: Optional[str] = None,
    since: Optional[datetime] = None,
    status: Optional[str] = None,
) -> List[ApplicationRow]:
    """Return active applications, filtered by criteria. Cached for 60s."""
    return _query.list_applications(company=company, since=since, status=status)


@st.cache_data(ttl=60)
def cached_weekly_summary(now: Optional[datetime] = None) -> WeeklySummary:
    """Return the last-7-days summary with pacing comparison."""
    return _query.weekly_summary(now=now)


@st.cache_data(ttl=60)
def cached_efficacy_by_template() -> List[EfficacyRow]:
    """Return per-template efficacy aggregations."""
    return _query.efficacy_by_template()


@st.cache_data(ttl=60)
def cached_find_duplicates(
    company: str,
    role_title: str,
    within_days: int = 60,
) -> List[ApplicationRow]:
    """Return applications to the same company+role within the window."""
    return _query.find_duplicates(company, role_title, within_days=within_days)


@st.cache_data(ttl=60)
def cached_list_resume_paths() -> list[str]:
    """Distinct resume file paths from the resume_versions table."""
    from scripts.tracker.query import open_db
    try:
        with open_db() as conn:
            cur = conn.execute("SELECT DISTINCT file_path FROM resume_versions WHERE file_path IS NOT NULL")
            return sorted({row[0] for row in cur.fetchall() if row[0]})
    except Exception:
        return []


@st.cache_data(ttl=60)
def cached_list_cover_letter_paths() -> list[str]:
    """Distinct cover-letter file paths from the cover_letters table."""
    from scripts.tracker.query import open_db
    try:
        with open_db() as conn:
            cur = conn.execute("SELECT DISTINCT file_path FROM cover_letters WHERE file_path IS NOT NULL")
            return sorted({row[0] for row in cur.fetchall() if row[0]})
    except Exception:
        return []


@st.cache_data(ttl=60)
def cached_list_jd_paths() -> list[str]:
    """Distinct JD source identifiers (URLs or file paths) from the jds table."""
    from scripts.tracker.query import open_db
    try:
        with open_db() as conn:
            cur = conn.execute("SELECT DISTINCT source FROM jds WHERE source IS NOT NULL")
            return sorted({row[0] for row in cur.fetchall() if row[0]})
    except Exception:
        return []


def clear_all_caches() -> None:
    """Clear every cached wrapper at once. Called by the sidebar global refresh."""
    cached_list_applications.clear()
    cached_weekly_summary.clear()
    cached_efficacy_by_template.clear()
    cached_find_duplicates.clear()
    cached_list_resume_paths.clear()
    cached_list_cover_letter_paths.clear()
    cached_list_jd_paths.clear()
