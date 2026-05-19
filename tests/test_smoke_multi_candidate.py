"""Smoke test: multi-candidate output flow (Approach C)."""
from datetime import datetime
from pathlib import Path

import pytest

from scripts.generators.resume_to_docx import render_resume_docx
from scripts.outputs.io import make_artifact_path, finalize_docx
from scripts.outputs.tagging import read_artifact_meta
from scripts.tracker.add import add_jd, add_resume_version
from scripts.tracker.profile import write_profile
from scripts.tracker.models import Profile


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    monkeypatch.setenv("BRAINS_OUTPUTS_DIR", str(tmp_path / "outputs"))
    write_profile(Profile(first_name="Matthew", last_name="Gell"))
    return tmp_path


def _minimal_data(name: str) -> dict:
    return {
        "candidate_name": name,
        "candidate_contact_line": "Somewhere, AU",
        "summary": "Test summary.",
        "skills": "Test skills.",
        "experience": "Role 1\nRole 2",
        "education": "School A",
    }


def test_two_candidates_one_installation(isolated):
    """Same installation produces UID-tagged DOCX for two different candidates."""
    jd_id = add_jd("manual", None, "Acme", "Sales Assistant", "...", {}, [], [])

    # Profile holder
    self_path, self_meta = make_artifact_path(jd_id, "resume", parent_uid=None)
    render_resume_docx(_minimal_data("Matthew Gell"), self_path, template="hybrid")
    finalize_docx(self_path, self_meta)
    add_resume_version(
        file_path=str(self_path), template="hybrid", focus_areas=[],
        tagged_jd_id=jd_id, artifact_uid=self_meta.artifact_uid,
    )

    # For someone else
    other_path, other_meta = make_artifact_path(
        jd_id, "resume", parent_uid=None, for_candidate="Mathilda Gell",
    )
    render_resume_docx(_minimal_data("Mathilda Gell"), other_path, template="hybrid")
    finalize_docx(other_path, other_meta)
    add_resume_version(
        file_path=str(other_path), template="hybrid", focus_areas=[],
        tagged_jd_id=jd_id, artifact_uid=other_meta.artifact_uid,
        for_candidate="Mathilda Gell",
    )

    assert self_path.exists()
    assert other_path.exists()
    assert self_path != other_path

    self_round = read_artifact_meta(self_path)
    other_round = read_artifact_meta(other_path)
    assert self_round.artifact_uid != other_round.artifact_uid
    assert self_round.for_candidate is None
    assert other_round.for_candidate == "Mathilda Gell"
    assert "Matthew" in self_path.name
    assert "Mathilda" in other_path.name
