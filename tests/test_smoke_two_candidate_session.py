"""End-to-end: two candidates in one installation."""
from pathlib import Path

import pytest

from scripts.generators.resume_to_docx import render_resume_docx
from scripts.outputs.io import make_artifact_path, finalize_docx
from scripts.outputs.tagging import read_artifact_meta
from scripts.tracker.add import add_jd, add_resume_version
from scripts.tracker.candidates import create_candidate, set_active_candidate, get_active_candidate
from scripts.tracker.query import list_jds, list_artifacts_for_candidate


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    monkeypatch.setenv("BRAINS_OUTPUTS_DIR", str(tmp_path / "outputs"))
    return tmp_path


def _data(name): return {
    "candidate_name": name,
    "candidate_contact_line": "Somewhere, AU",
    "summary": "Test.", "skills": "Test.",
    "experience": "Role", "education": "School",
}


def test_two_candidate_session_end_to_end(isolated):
    matthew = create_candidate("Matthew", "Gell", ["data eng"], 5, None)
    mathilda = create_candidate("Mathilda", "Gell", ["retail"], 2, None)

    # Matthew's path
    set_active_candidate(matthew)
    jd1 = add_jd("manual", None, "Acme", "Sr Eng", "...", {}, [], [])
    path1, meta1 = make_artifact_path(jd1, "resume")
    render_resume_docx(_data("Matthew Gell"), path1, template="hybrid")
    finalize_docx(path1, meta1)
    add_resume_version(
        file_path=str(path1), template="hybrid", focus_areas=[],
        tagged_jd_id=jd1, artifact_uid=meta1.artifact_uid,
    )

    # Mathilda's path
    set_active_candidate(mathilda)
    jd2 = add_jd("manual", None, "Big W", "Sales Assistant", "...", {}, [], [])
    path2, meta2 = make_artifact_path(jd2, "resume")
    render_resume_docx(_data("Mathilda Gell"), path2, template="hybrid")
    finalize_docx(path2, meta2)
    add_resume_version(
        file_path=str(path2), template="hybrid", focus_areas=[],
        tagged_jd_id=jd2, artifact_uid=meta2.artifact_uid,
    )

    # Filenames distinct
    assert "Matthew" in path1.name
    assert "Mathilda" in path2.name

    # DOCX custom-property round-trip
    m1 = read_artifact_meta(path1)
    m2 = read_artifact_meta(path2)
    assert m1.candidate_id == matthew
    assert m2.candidate_id == mathilda

    # Tab-scope behaviour
    set_active_candidate(matthew)
    assert {jd.company for jd in list_jds()} == {"Acme"}
    set_active_candidate(mathilda)
    assert {jd.company for jd in list_jds()} == {"Big W"}

    # Name lookup
    rows = list_artifacts_for_candidate("Mathilda Gell")
    assert len(rows) == 1
    assert rows[0].candidate_id == mathilda
