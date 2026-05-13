"""Dataclasses for the tracker entities.

These are the data-transfer types between the public API (add/query/profile)
and consumers. They map 1:1 to SQLite rows for the 5 entity tables, plus
Profile (lives in profile.json), WeeklySummary (computed), and EfficacyRow
(computed).
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional


# Event-type enum values for the outcomes table. Defined as a tuple so they
# can be imported and used as the canonical list (e.g. for CLI validation).
OUTCOME_EVENT_TYPES = (
    "acknowledged",
    "callback",
    "phone_screen",
    "first_round",
    "second_round",
    "take_home",
    "offer",
    "rejection",
    "ghosted",
    "withdrew",
)

# Channel enum values for the applications table.
APPLICATION_CHANNELS = (
    "linkedin",
    "agency",
    "direct",
    "referral",
    "other",
)


@dataclass
class ResumeVersion:
    id: Optional[int]
    file_path: Optional[str]
    template: str
    focus_areas: List[str]
    parent_id: Optional[int]
    tagged_jd_id: Optional[int]
    created_at: str
    archived_at: Optional[str]


@dataclass
class CoverLetter:
    id: Optional[int]
    file_path: Optional[str]
    resume_version_id: int
    jd_id: int
    template: str
    created_at: str
    archived_at: Optional[str]


@dataclass
class JD:
    id: Optional[int]
    source: str
    source_ref: Optional[str]
    company: str
    role_title: str
    raw_text: str
    analyzer_findings: dict
    focus_areas_required: List[str]
    focus_areas_nice: List[str]
    created_at: str
    archived_at: Optional[str]


@dataclass
class Application:
    id: Optional[int]
    jd_id: int
    resume_version_id: int
    cover_letter_id: Optional[int]
    submitted_at: str
    channel: str
    agency_name: Optional[str]
    recruiter_contact: Optional[str]
    notes: Optional[str]
    created_at: str
    archived_at: Optional[str]


@dataclass
class Outcome:
    id: Optional[int]
    application_id: int
    event_type: str
    event_date: str
    notes: Optional[str]
    created_at: str
    archived_at: Optional[str]


@dataclass
class Profile:
    focus_areas: List[str] = field(default_factory=list)
    healthy_weekly_rate: Optional[int] = None


@dataclass
class WeeklySummary:
    week_starting: str  # YYYY-MM-DD (Monday of the week)
    applications_count: int
    outcomes_by_type: Dict[str, int]
    pacing_vs_target: Optional[str]  # 'above' | 'at' | 'below' | None if no target


@dataclass
class EfficacyRow:
    template: str
    submitted_count: int
    callback_count: int
    interview_count: int  # phone_screen + first_round + second_round + take_home
    offer_count: int
    rejection_count: int
