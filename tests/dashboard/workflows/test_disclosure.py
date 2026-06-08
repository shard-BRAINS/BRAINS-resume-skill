"""Tests for the disclosure dashboard surface — focused on the pure helpers.

The Streamlit render() function depends on session_state and isn't unit-tested
directly here; the suggest_strength algorithm and module wiring are.
"""
import pytest

from scripts.dashboard.workflows.disclosure import (
    FACTOR_QUESTIONS, suggest_strength, _is_strong_yes, _format_strength_label,
)


# ---------------------------------------------------------------------------
# _is_strong_yes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("answer,expected", [
    ("yes", True),
    ("Yes", True),
    ("YES", True),
    ("Yes — formal employer programme", True),
    ("yes, conditional on employer", True),
    ("Conditional yes — employer/role dependent", False),  # leads with 'Conditional'
    ("no", False),
    ("No.", False),
    ("Unsure", False),
    ("", False),
    (None, False),
    ("  yes  ", True),
])
def test_is_strong_yes(answer, expected):
    assert _is_strong_yes(answer) is expected


# ---------------------------------------------------------------------------
# suggest_strength
# ---------------------------------------------------------------------------

def test_suggest_default_position_when_no_yeses():
    """No factor answers → default holds → non-disclosure."""
    assert suggest_strength({}) == "non-disclosure"


def test_suggest_neutral_with_two_structural_yeses():
    assert suggest_strength({
        "factor_1": "Yes",
        "factor_2": "Yes",
        "factor_3": "No",
        "factor_5": "No",
    }) == "neutral"


def test_suggest_explicit_with_three_structural_yeses():
    assert suggest_strength({
        "factor_1": "Yes — formal programme verified",
        "factor_2": "Yes — accessibility role",
        "factor_3": "Yes — community channel",
        "factor_4": "No",
        "factor_5": "No",
    }) == "explicit"


def test_suggest_explicit_with_all_four_structural_yeses():
    assert suggest_strength({
        "factor_1": "Yes",
        "factor_2": "Yes",
        "factor_3": "Yes",
        "factor_5": "Yes",
    }) == "explicit"


def test_factor_4_bumps_non_disclosure_to_neutral():
    """Need accommodation at application stage → at least neutral."""
    assert suggest_strength({"factor_4": "Yes"}) == "neutral"


def test_factor_4_bumps_neutral_to_explicit():
    assert suggest_strength({
        "factor_1": "Yes",
        "factor_2": "Yes",
        "factor_4": "Yes",
    }) == "explicit"


def test_factor_4_does_not_bump_explicit_above():
    """No level above 'explicit' — factor 4 caps there."""
    assert suggest_strength({
        "factor_1": "Yes", "factor_2": "Yes", "factor_3": "Yes",
        "factor_4": "Yes", "factor_5": "Yes",
    }) == "explicit"


def test_factor_6_is_informational_only():
    """Professional advice received doesn't shift the algorithm's suggestion."""
    without_six = suggest_strength({"factor_1": "Yes"})
    with_six = suggest_strength({"factor_1": "Yes", "factor_6": "Yes"})
    assert without_six == with_six


def test_conditional_yes_does_not_count_as_strong_yes():
    """The May 2026 exemplar's 'conditional yes' phrasing is not a strong-yes."""
    result = suggest_strength({
        "factor_1": "Yes",
        "factor_2": "Yes",
        "factor_3": "Yes",
        "factor_5": "Conditional yes — employer/role dependent",
    })
    # Only 3 structural yeses count (1,2,3) — explicit.
    assert result == "explicit"


def test_only_factor_1_and_2_drives_neutral_via_factor_4():
    """Two structural yeses → neutral; factor 4 bumps to explicit."""
    result = suggest_strength({
        "factor_1": "Yes", "factor_2": "Yes",
        "factor_4": "Yes — need written interview format",
    })
    assert result == "explicit"


# ---------------------------------------------------------------------------
# Misc structural sanity
# ---------------------------------------------------------------------------

def test_factor_questions_count():
    """All six factors are surfaced as inputs."""
    assert len(FACTOR_QUESTIONS) == 6
    assert [f[0] for f in FACTOR_QUESTIONS] == [
        "factor_1", "factor_2", "factor_3", "factor_4", "factor_5", "factor_6",
    ]


def test_format_strength_label_maps_known_values():
    assert _format_strength_label("non-disclosure") == "Non-disclosure"
    assert _format_strength_label("neutral") == "Neutral signalling"
    assert _format_strength_label("explicit") == "Explicit disclosure"
    assert _format_strength_label("undecided") == "Undecided"


def test_format_strength_label_passes_through_unknown():
    assert _format_strength_label("brand-new-strength") == "brand-new-strength"


# ---------------------------------------------------------------------------
# Light integration — saving via the CRUD pathway used by the form
# ---------------------------------------------------------------------------

@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    monkeypatch.setenv("BRAINS_OUTPUTS_DIR", str(tmp_path / "outputs"))
    return tmp_path


def test_form_save_path_records_session(isolated):
    """Smoke: the CRUD calls the form makes round-trip cleanly."""
    from scripts.tracker.candidates import create_candidate
    from scripts.tracker import disclosure as disclosure_db
    cid = create_candidate("Matthew", "Gell", [], None, None)
    sid = disclosure_db.create_session(
        candidate_id=cid,
        landed_strength="neutral",
        target_employer="Acme",
        target_role="Designer",
        factor_1="Yes",
        factor_2="Yes",
        notes="from-form",
    )
    sessions = disclosure_db.list_sessions_for_candidate(cid)
    assert len(sessions) == 1 and sessions[0].id == sid
    assert sessions[0].notes == "from-form"


def test_history_excludes_archived(isolated):
    from scripts.tracker.candidates import create_candidate
    from scripts.tracker import disclosure as disclosure_db
    cid = create_candidate("Matthew", "Gell", [], None, None)
    s1 = disclosure_db.create_session(candidate_id=cid, landed_strength="non-disclosure")
    s2 = disclosure_db.create_session(candidate_id=cid, landed_strength="neutral")
    disclosure_db.archive_session(s1)
    visible = disclosure_db.list_sessions_for_candidate(cid)
    assert [s.id for s in visible] == [s2]


def test_full_save_and_generate_pathway(isolated):
    """Smoke: the save+generate button's call chain works end-to-end."""
    from scripts.tracker.candidates import create_candidate
    from scripts.tracker import disclosure as disclosure_db
    from scripts.generators.disclosure_worksheet import generate
    cid = create_candidate("Matthew", "Gell", [], None, None)
    sid = disclosure_db.create_session(
        candidate_id=cid,
        landed_strength="explicit",
        factor_1="Yes",
        factor_2="Yes",
        factor_3="Yes",
    )
    md_path, pdf_path = generate(sid)
    assert md_path.exists() and pdf_path.exists()
    refreshed = disclosure_db.get_session(sid)
    assert refreshed.artifact_uid is not None
