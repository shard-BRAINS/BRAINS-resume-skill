"""Tests for the profile.json read/write helpers.

Post-Approach-B: the profile holds two fields only — active_candidate_id and
log_handoffs. Per-candidate data lives in the candidates table. A legacy-shape
profile.json (with first_name/focus_areas/etc) reads as an empty Profile; the
legacy fields are consumed by the Task 5 backfill hook, not here.
"""
from pathlib import Path

from scripts.tracker.models import Profile
from scripts.tracker.profile import read_profile, write_profile, get_profile_path


def test_get_profile_path_default(monkeypatch):
    monkeypatch.delenv("BRAINS_TRACKER_PROFILE_PATH", raising=False)
    assert get_profile_path() == Path.home() / ".brains-resume" / "profile.json"


def test_get_profile_path_honours_env_override(monkeypatch, tmp_path):
    override = tmp_path / "custom.json"
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(override))
    assert get_profile_path() == override


def test_read_profile_when_file_missing_returns_empty(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "missing.json"))
    p = read_profile()
    assert p.active_candidate_id is None
    assert p.log_handoffs is True


def test_read_profile_malformed_json_returns_empty(monkeypatch, tmp_path):
    path = tmp_path / "p.json"
    path.write_text("this is not json", encoding="utf-8")
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(path))
    p = read_profile()
    # Defensive default — corrupt file should not crash, just return empty.
    assert p.active_candidate_id is None
    assert p.log_handoffs is True


def test_profile_default_log_handoffs_is_true():
    p = Profile()
    assert p.log_handoffs is True


def test_read_profile_trimmed_shape(tmp_path, monkeypatch):
    """A profile.json in the post-B trimmed shape reads cleanly."""
    p = tmp_path / "profile.json"
    p.write_text('{"active_candidate_id": 5, "log_handoffs": false}', encoding="utf-8")
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(p))

    from scripts.tracker.profile import read_profile
    prof = read_profile()
    assert prof.active_candidate_id == 5
    assert prof.log_handoffs is False


def test_read_profile_legacy_shape_returns_empty(tmp_path, monkeypatch):
    """A profile.json in the pre-B legacy shape reads as an empty Profile.

    The legacy fields (first_name/last_name/focus_areas/...) are not on the
    new Profile dataclass; they are consumed by the backfill hook only.
    """
    p = tmp_path / "profile.json"
    p.write_text(
        '{"first_name": "Matthew", "last_name": "Gell",'
        ' "focus_areas": ["data eng"], "healthy_weekly_rate": 5,'
        ' "log_handoffs": true}',
        encoding="utf-8",
    )
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(p))

    from scripts.tracker.profile import read_profile
    prof = read_profile()
    assert prof.active_candidate_id is None
    assert prof.log_handoffs is True


def test_write_profile_writes_trimmed_shape(tmp_path, monkeypatch):
    from scripts.tracker.profile import write_profile
    from scripts.tracker.models import Profile

    p = tmp_path / "profile.json"
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(p))
    write_profile(Profile(active_candidate_id=7, log_handoffs=False))

    import json
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data == {"active_candidate_id": 7, "log_handoffs": False}


def test_write_then_read_round_trip(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "p.json"))
    write_profile(Profile(active_candidate_id=3, log_handoffs=True))
    p = read_profile()
    assert p.active_candidate_id == 3
    assert p.log_handoffs is True


def test_write_profile_creates_parent_dir(monkeypatch, tmp_path):
    target = tmp_path / "newdir" / "p.json"
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(target))
    write_profile(Profile())
    assert target.exists()


def test_read_profile_missing_log_handoffs_defaults_to_true(monkeypatch, tmp_path):
    path = tmp_path / "p.json"
    path.write_text('{"active_candidate_id": 2}', encoding="utf-8")
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(path))
    p = read_profile()
    assert p.log_handoffs is True
