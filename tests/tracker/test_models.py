"""Tests for tracker dataclass models."""
from scripts.tracker.models import (
    APPLICATION_CHANNELS,
    OUTCOME_EVENT_TYPES,
    Application,
    CoverLetter,
    EfficacyRow,
    JD,
    Outcome,
    Profile,
    ResumeVersion,
    WeeklySummary,
)


def test_outcome_event_types_complete():
    """The enum must include every event type the spec calls for."""
    expected = {
        "acknowledged", "callback", "phone_screen", "first_round",
        "second_round", "take_home", "offer", "rejection",
        "ghosted", "withdrew",
    }
    assert set(OUTCOME_EVENT_TYPES) == expected


def test_application_channels_complete():
    expected = {"linkedin", "agency", "direct", "referral", "other"}
    assert set(APPLICATION_CHANNELS) == expected


def test_profile_default_empty():
    p = Profile()
    assert p.focus_areas == []
    assert p.healthy_weekly_rate is None


def test_resume_version_all_fields_present():
    rv = ResumeVersion(
        id=1,
        file_path="/tmp/r.docx",
        template="hybrid",
        focus_areas=["platform", "observability"],
        parent_id=None,
        tagged_jd_id=None,
        created_at="2026-05-13T00:00:00Z",
        archived_at=None,
    )
    assert rv.template == "hybrid"
    assert rv.focus_areas == ["platform", "observability"]


def test_jd_carries_analyzer_findings_dict():
    jd = JD(
        id=1, source="paste", source_ref=None,
        company="Example Corp", role_title="Senior Engineer",
        raw_text="JD text", analyzer_findings={"red_flags": 2},
        focus_areas_required=["python"], focus_areas_nice=["go"],
        created_at="2026-05-13T00:00:00Z", archived_at=None,
    )
    assert jd.analyzer_findings == {"red_flags": 2}


def test_efficacy_row_carries_per_template_counts():
    e = EfficacyRow(
        template="hybrid", submitted_count=10, callback_count=4,
        interview_count=2, offer_count=1, rejection_count=3,
    )
    assert e.template == "hybrid"
    assert e.submitted_count == 10
