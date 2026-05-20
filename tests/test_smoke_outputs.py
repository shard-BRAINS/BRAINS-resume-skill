"""End-to-end smoke for the v1.5.0 outputs pipeline.

Exercises: add_jd -> ensure_jd_folder -> make_artifact_path ->
render_resume_docx (with meta) -> add_resume_version -> find_artifact_by_uid.
"""
import pytest

from scripts.generators.resume_to_docx import render_resume_docx
from scripts.outputs.io import (
    ensure_jd_folder,
    make_artifact_path,
    find_artifact_by_uid,
)
from scripts.outputs.tagging import read_artifact_meta
from scripts.tracker.add import add_jd, add_resume_version
from scripts.tracker.candidates import create_candidate, set_active_candidate


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    monkeypatch.setenv("BRAINS_OUTPUTS_DIR", str(tmp_path / "outputs"))
    return tmp_path


def test_smoke_full_chain(isolated):
    # Set up the active candidate.
    cid = create_candidate("Matthew", "Gell", [], None, None)
    set_active_candidate(cid)

    # Add a JD; folder is created and path recorded.
    jd_id = add_jd(
        source="manual", source_ref=None,
        company="Acme Corp", role_title="Senior Data Engineer",
        raw_text="...", analyzer_findings={}, focus_areas_required=[],
        focus_areas_nice=[],
    )
    folder = ensure_jd_folder(jd_id)
    assert folder.exists()

    # Reserve an artifact path + meta.
    path, meta = make_artifact_path(jd_id, "resume")

    # Render the resume with meta embedded.
    render_resume_docx(
        data={
            "candidate_name": "Matthew Gell",
            "candidate_contact_line": "m@example.com",
            "summary": "Senior data engineer.",
            "skills": "Python\nSQL",
            "experience": "Engineer @ Co (2020-2026)",
            "education": "BSc Computer Science",
        },
        out_path=path,
        template="chronological",
        artifact_meta=meta,
    )
    assert path.exists()

    # Tracker write.
    rv_id = add_resume_version(
        file_path=str(path), template="chronological",
        focus_areas=[], parent_id=None, tagged_jd_id=jd_id,
        artifact_uid=meta.artifact_uid,
    )

    # Look up by uid — should find the resume row.
    found = find_artifact_by_uid(meta.artifact_uid)
    assert found is not None
    assert found.id == rv_id
    assert found.file_path == str(path)

    # Embedded meta round-trips.
    loaded = read_artifact_meta(path)
    assert loaded.artifact_uid == meta.artifact_uid

    # Rename the file; lookup by UID still works (filename irrelevant).
    renamed = path.parent / "manual-rename.docx"
    path.rename(renamed)
    loaded2 = read_artifact_meta(renamed)
    assert loaded2.artifact_uid == meta.artifact_uid
