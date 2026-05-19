"""Tests for scripts/outputs/io.py — orchestration layer."""
from pathlib import Path

import pytest

from scripts.outputs.io import (
    get_outputs_root,
    ProfileNameMissingError,
    OutputsDirNotWritableError,
    UIDCollisionError,
)


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    """Each test gets isolated DB, profile, and outputs root."""
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    monkeypatch.setenv("BRAINS_OUTPUTS_DIR", str(tmp_path / "outputs"))
    return tmp_path


def test_get_outputs_root_honours_env_var(isolated):
    assert get_outputs_root() == isolated / "outputs"


def test_get_outputs_root_defaults_when_unset(monkeypatch):
    monkeypatch.delenv("BRAINS_OUTPUTS_DIR", raising=False)
    assert get_outputs_root() == Path.home() / ".brains-resume" / "outputs"


def test_exceptions_are_distinct():
    # Sanity: the three exception classes exist and aren't the same.
    assert ProfileNameMissingError is not OutputsDirNotWritableError
    assert ProfileNameMissingError is not UIDCollisionError
    assert OutputsDirNotWritableError is not UIDCollisionError
