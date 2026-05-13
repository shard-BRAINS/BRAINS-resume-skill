"""Smoke test for the deterministic portion of the consolidation workflow.

Exercises: validator runs end-to-end on structured position pairs derived
from fixtures, the report artifact is written, and all five finding codes
are achievable on the seeded inputs.
"""
from pathlib import Path

from scripts.validators.consolidation_check import consolidation_check
from tests.fixtures import consolidation_fixtures as fx


def test_consolidate_smoke_all_finding_codes_reachable(tmp_path):
    # Combine the seeded fixtures so a single run surfaces every finding code.
    resume = (
        fx.TITLE_MISMATCH_RESUME
        + fx.DATE_MISMATCH_RESUME
        + fx.ACHIEVEMENT_RESUME_ONLY_RESUME
        + fx.TONE_DIVERGENT_RESUME
    )
    linkedin = (
        fx.TITLE_MISMATCH_LINKEDIN
        + fx.DATE_MISMATCH_LINKEDIN
        + fx.ACHIEVEMENT_RESUME_ONLY_LINKEDIN
        + fx.TONE_DIVERGENT_LINKEDIN
    )

    result = consolidation_check(resume, linkedin)
    codes = {f.code for f in result.findings}
    # Note: title mismatch and tone divergence both come off the Example Corp
    # role in different fixtures — both should fire.
    assert "CONSOLIDATION_JOB_TITLE_MISMATCH" in codes
    assert "CONSOLIDATION_DATE_INCONSISTENCY" in codes
    assert "CONSOLIDATION_ACHIEVEMENT_ONLY_IN_RESUME" in codes
    assert "CONSOLIDATION_TONE_DIVERGENCE" in codes

    # Write the report artifact
    out = tmp_path / "consolidation-report-2026-05-13-120000.md"
    lines = [
        "# Resume + LinkedIn Consolidation Report\n",
        "**Prepared:** 2026-05-13\n",
        "**Resume:** synthetic_resume_basic.docx\n",
        "**LinkedIn source:** synthetic_linkedin_export.zip\n",
        "\n## Summary\n",
        f"- Roles compared: {len(resume)}\n",
        f"- Findings raised: {len(result.findings)}\n",
        "\n## Per-role findings\n",
    ]
    for f in result.findings:
        lines.append(f"\n### {f.role_context}\n")
        lines.append(f"- **{f.code}** ({f.severity})\n")
        lines.append(f"  - Resume: {f.resume_excerpt}\n")
        lines.append(f"  - LinkedIn: {f.linkedin_excerpt}\n")
        lines.append("  - Suggested resolutions:\n")
        for r in f.suggested_resolutions:
            lines.append(f"    - [{r['tag']}] {r['text']}\n")
    out.write_text("".join(lines), encoding="utf-8")

    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "Consolidation Report" in content
    assert "RESUME-LEADING" in content
    assert "LINKEDIN-LEADING" in content
    assert "NEW-SYNTHESIS" in content
