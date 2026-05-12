"""Smoke test for the deterministic portion of the tailor-to-JD workflow."""
from pathlib import Path

from scripts.parsers.jd_url_fetch import fetch_jd_from_html
from scripts.validators.bias_scan import bias_scan
from scripts.validators.integrity_check import integrity_check
from scripts.generators.resume_to_docx import render_resume_docx

JD_HTML = """
<html><body><main>
<h1>Senior Engineer</h1>
<p>Python distributed systems observability mentoring.</p>
<h2>Requirements</h2><ul><li>8+ years experience</li></ul>
</main></body></html>
"""


def test_tailor_workflow_deterministic_pipeline(tmp_path):
    jd_result = fetch_jd_from_html(JD_HTML)
    assert jd_result["error"] is None
    jd_text = jd_result["text"]
    assert "Senior Engineer" in jd_text

    tailored = {
        "candidate_name": "Alex Test",
        "candidate_contact_line": "alex.test@example.invalid | Sample City",
        "summary": "Senior engineer aligned to distributed-systems roles requiring mentoring experience.",
        "skills": "Python, distributed systems, observability, mentoring",
        "experience": "Senior Engineer, Example Corp 2020 - Present\nBuilt ingestion pipeline.",
        "education": "BSc Computer Science, Example University, 2015",
    }
    text_blob = "\n".join(str(v) for v in tailored.values())
    bias_scan(text_blob)
    integrity_check(text_blob)

    out = tmp_path / "tailored.docx"
    render_resume_docx(tailored, out)
    assert out.exists()
