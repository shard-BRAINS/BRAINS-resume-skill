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

# Disclosure-strength values for the disclosure_sessions table.
# `undecided` lets a coaching session that didn't reach a decision still be
# recorded — the downstream auto-apply treats it as "no preference on file".
DISCLOSURE_STRENGTHS = (
    "non-disclosure",
    "neutral",
    "explicit",
    "undecided",
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
    artifact_uid: Optional[str] = None
    parent_uid: Optional[str] = None
    for_candidate: Optional[str] = None
    candidate_id: Optional[int] = None


@dataclass
class Candidate:
    id: Optional[int]
    first_name: str
    last_name: str
    focus_areas: List[str]
    healthy_weekly_rate: Optional[int]
    pacing_notes: Optional[str]
    created_at: str
    archived_at: Optional[str]
    email: Optional[str] = None
    career_stage: Optional[str] = None
    direction: Optional[str] = None
    target_roles: List[str] = field(default_factory=list)
    target_industries: List[str] = field(default_factory=list)
    leadership_intent: Optional[str] = None
    work_preferences: List[str] = field(default_factory=list)
    location: Optional[str] = None
    relocation_open: Optional[int] = None
    role_priorities: Optional[str] = None
    timeline: Optional[str] = None
    intent_collected_at: Optional[str] = None


@dataclass
class CoverLetter:
    id: Optional[int]
    file_path: Optional[str]
    resume_version_id: int
    jd_id: int
    template: str
    created_at: str
    archived_at: Optional[str]
    artifact_uid: Optional[str] = None
    parent_uid: Optional[str] = None
    for_candidate: Optional[str] = None
    candidate_id: Optional[int] = None


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
    folder_path: Optional[str] = None
    candidate_id: Optional[int] = None


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
class DisclosureSession:
    id: Optional[int]
    candidate_id: int
    created_at: str
    landed_strength: str
    target_employer: Optional[str] = None
    target_role: Optional[str] = None
    factor_1: Optional[str] = None
    factor_2: Optional[str] = None
    factor_3: Optional[str] = None
    factor_4: Optional[str] = None
    factor_5: Optional[str] = None
    factor_6: Optional[str] = None
    notes: Optional[str] = None
    artifact_uid: Optional[str] = None
    archived_at: Optional[str] = None


@dataclass
class Profile:
    active_candidate_id: Optional[int] = None
    log_handoffs: bool = True


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
