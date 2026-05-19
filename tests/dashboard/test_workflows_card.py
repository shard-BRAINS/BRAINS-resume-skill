"""Tests for the shared workflow-card helper."""
from pathlib import Path


def test_collect_args_filters_none_and_empty():
    from scripts.dashboard.workflows._card import collect_args
    assert collect_args([Path("a.docx"), None, "", "b.txt"]) == ["a.docx", "b.txt"]


def test_collect_args_stringifies_paths(tmp_path):
    from scripts.dashboard.workflows._card import collect_args
    p = tmp_path / "r.docx"
    p.write_bytes(b"")
    result = collect_args([p])
    assert result == [str(p)]


def test_collect_args_passes_strings_through():
    from scripts.dashboard.workflows._card import collect_args
    assert collect_args(["https://jd.url", "extra"]) == ["https://jd.url", "extra"]


def test_collect_args_all_none_returns_empty():
    from scripts.dashboard.workflows._card import collect_args
    assert collect_args([None, None]) == []


def test_create_workflow_passes_for_candidate_to_artifact_meta(monkeypatch, tmp_path):
    """When the user fills the for_candidate text input, it lands on ArtifactMeta."""
    from scripts.dashboard.workflows import create as create_mod
    from scripts.outputs.tagging import ArtifactMeta

    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    monkeypatch.setenv("BRAINS_OUTPUTS_DIR", str(tmp_path / "outputs"))

    from scripts.tracker.profile import write_profile
    from scripts.tracker.models import Profile
    write_profile(Profile(first_name="Matthew", last_name="Gell"))

    captured = {}
    def fake_make_artifact_path(jd_id, kind, parent_uid=None, for_candidate=None):
        captured["for_candidate"] = for_candidate
        path = tmp_path / "fake.docx"
        meta = ArtifactMeta(
            artifact_uid="ABC123", artifact_kind=kind,
            jd_id=jd_id, parent_uid=parent_uid,
            created_at="2026-05-19T00:00:00Z", skill_version="1.5.0",
            for_candidate=for_candidate,
        )
        return path, meta

    monkeypatch.setattr(create_mod, "make_artifact_path", fake_make_artifact_path)
    target_path, meta = create_mod._resolve_target(
        jd_id=1, for_candidate="Mathilda Gell",
    )
    assert captured["for_candidate"] == "Mathilda Gell"
    assert meta.for_candidate == "Mathilda Gell"


def test_jd_analyze_persists_jd_and_analysis_to_folder(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    monkeypatch.setenv("BRAINS_OUTPUTS_DIR", str(tmp_path / "outputs"))
    from scripts.dashboard.workflows.jd_analyze import persist_analyzed_jd
    findings = {"role_fit_score": 7, "red_flags": []}
    jd_id, folder = persist_analyzed_jd(
        raw_text="Senior Data Engineer at Acme...",
        company="Acme",
        role_title="Senior Data Engineer",
        source="manual",
        source_ref=None,
        analyzer_findings=findings,
        focus_areas_required=[],
        focus_areas_nice=[],
    )
    assert (folder / "jd.txt").exists()
    assert (folder / "jd.txt").read_text(encoding="utf-8").startswith("Senior Data Engineer")
    assert (folder / "jd-analysis.md").exists()
    assert "role_fit_score" in (folder / "jd-analysis.md").read_text(encoding="utf-8")
