"""Smoke test for the deterministic portion of the LinkedIn-improve workflow.

Exercises: parse synthetic LinkedIn export, run bias_scan + integrity_check on
a representative rewritten output, write the markdown artifact file. The
rewrite itself is Claude-driven and not deterministically testable here —
this smoke test verifies the surrounding scaffolding works end-to-end.
"""
from pathlib import Path

from scripts.parsers.linkedin_zip import parse_linkedin_export
from scripts.validators.bias_scan import bias_scan
from scripts.validators.integrity_check import integrity_check

PROJECT_ROOT = Path(__file__).parent.parent
FIXTURE_ZIP = PROJECT_ROOT / "docs" / "testing" / "fixtures" / "synthetic_linkedin_export.zip"


# Representative output a well-formed rewrite would produce. Used to validate
# the validator pipeline; the actual rewriting is Claude-driven at runtime.
REWRITTEN_SAMPLE = (
    "Senior platform engineer focused on observability and incident response. "
    "Built distributed-systems instrumentation for 50M-DAU products. "
    "Open to staff and principal roles in observability, reliability, and platform.\n\n"
    "I build observability and reliability platforms. At Example Corp I led the migration "
    "of a 50M-DAU ingestion pipeline to a unified telemetry layer, cutting p99 latency "
    "by 40 percent and reducing operator-on-call load by half.\n\n"
    "I previously led the platform-engineering team at Sample Industries, where we "
    "consolidated four service-monitoring stacks into one and trained four engineers "
    "to senior level. I care about systems that humans can actually operate.\n\n"
    "Currently open to staff or principal platform-engineering roles where "
    "observability is treated as a first-class product surface.\n\n"
    "Skills: Python, distributed systems, observability, incident response, OpenTelemetry, "
    "Prometheus, SLO design, platform engineering, mentoring, technical leadership, "
    "Kubernetes, AWS, GCP, Terraform, Go, service-mesh, on-call ergonomics"
)


def test_linkedin_improve_smoke(tmp_path):
    # (a) Parse the synthetic LinkedIn export — same parser as linkedin-ingest.
    parsed = parse_linkedin_export(FIXTURE_ZIP)
    assert parsed["profile"], "synthetic profile section should not be empty"
    assert "Connections.csv" in parsed["skipped_files"]

    # (b) Run validators on a representative rewritten output.
    bias = bias_scan(REWRITTEN_SAMPLE)
    integ = integrity_check(REWRITTEN_SAMPLE)

    # The sample is intentionally clean — no CRITICAL/HIGH integrity findings.
    assert not any(f.severity in ("CRITICAL", "HIGH") for f in integ.findings), (
        f"Sample triggered unexpected integrity findings: "
        f"{[(f.code, f.severity) for f in integ.findings]}"
    )

    # (c) Write the markdown artifact.
    out = tmp_path / "linkedin-profile-2026-05-13-120000.md"
    out.write_text(
        "# LinkedIn Profile Rewrite\n\n"
        "**Prepared:** 2026-05-13\n"
        "**Target role / focus:** Staff platform engineering\n"
        "**Disclosure stance:** Affirmative framing (default)\n\n"
        "---\n\n"
        "## Headline\n\n"
        f"{REWRITTEN_SAMPLE.splitlines()[0]}\n\n"
        "## About\n\n"
        f"{REWRITTEN_SAMPLE}\n\n"
        f"_Bias findings on output:_ {len(bias.findings)}\n"
        f"_Integrity findings on output:_ {len(integ.findings)}\n",
        encoding="utf-8",
    )

    assert out.exists()
    assert out.stat().st_size > 0
    content = out.read_text(encoding="utf-8")
    assert "LinkedIn Profile Rewrite" in content
    assert "Headline" in content
    assert "About" in content
