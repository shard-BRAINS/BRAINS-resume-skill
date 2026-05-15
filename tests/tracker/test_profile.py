"""Tests for the profile.json read/write helpers."""
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
    assert p.focus_areas == []
    assert p.healthy_weekly_rate is None


def test_write_then_read_round_trip(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "p.json"))
    write_profile(Profile(focus_areas=["platform", "observability"], healthy_weekly_rate=4))
    p = read_profile()
    assert p.focus_areas == ["platform", "observability"]
    assert p.healthy_weekly_rate == 4


def test_write_profile_creates_parent_dir(monkeypatch, tmp_path):
    target = tmp_path / "newdir" / "p.json"
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(target))
    write_profile(Profile(focus_areas=["x"], healthy_weekly_rate=None))
    assert target.exists()


def test_write_profile_overwrites_existing(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "p.json"))
    write_profile(Profile(focus_areas=["a"], healthy_weekly_rate=3))
    write_profile(Profile(focus_areas=["b", "c"], healthy_weekly_rate=5))
    p = read_profile()
    assert p.focus_areas == ["b", "c"]
    assert p.healthy_weekly_rate == 5


def test_read_profile_malformed_json_returns_empty(monkeypatch, tmp_path):
    path = tmp_path / "p.json"
    path.write_text("this is not json", encoding="utf-8")
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(path))
    p = read_profile()
    # Defensive default — corrupt file should not crash, just return empty.
    assert p.focus_areas == []
    assert p.healthy_weekly_rate is None


def test_pacing_notes_round_trip(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "p.json"))
    write_profile(Profile(
        focus_areas=["python"], healthy_weekly_rate=3,
        pacing_notes="Felt overwhelming this week.",
    ))
    p = read_profile()
    assert p.pacing_notes == "Felt overwhelming this week."


def test_pacing_notes_backward_compat_missing_field(monkeypatch, tmp_path):
    """Old profile.json files without pacing_notes should still read cleanly."""
    path = tmp_path / "p.json"
    path.write_text('{"focus_areas": ["x"], "healthy_weekly_rate": 5}', encoding="utf-8")
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(path))
    p = read_profile()
    assert p.pacing_notes is None
    assert p.focus_areas == ["x"]
    assert p.healthy_weekly_rate == 5


def test_profile_default_log_handoffs_is_true():
    p = Profile()
    assert p.log_handoffs is True


def test_read_profile_missing_log_handoffs_defaults_to_true(monkeypatch, tmp_path):
    path = tmp_path / "p.json"
    path.write_text('{"focus_areas": ["A"], "healthy_weekly_rate": 5}', encoding="utf-8")
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(path))
    p = read_profile()
    assert p.log_handoffs is True


def test_write_profile_persists_log_handoffs_false(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "p.json"))
    write_profile(Profile(focus_areas=["X"], healthy_weekly_rate=4, log_handoffs=False))
    data = (tmp_path / "p.json").read_text(encoding="utf-8")
    assert '"log_handoffs": false' in data


def test_round_trip_log_handoffs_false(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "p.json"))
    write_profile(Profile(focus_areas=["X"], healthy_weekly_rate=4, log_handoffs=False))
    p = read_profile()
    assert p.log_handoffs is False
