"""Tests for the job-description URL fetcher.

Uses a local HTML fixture file via file:// URL to keep tests offline-reliable.
"""
from pathlib import Path
import pytest

from scripts.parsers.jd_url_fetch import fetch_jd_from_url, fetch_jd_from_html

FIXTURE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Senior Engineer - Example Corp</title></head>
<body>
<header>Example Corp Careers</header>
<main>
<h1>Senior Engineer</h1>
<p>We are looking for a senior engineer to join our distributed systems team.</p>
<h2>Responsibilities</h2>
<ul>
<li>Design and operate ingestion pipelines at scale</li>
<li>Mentor mid-level engineers</li>
<li>Contribute to architecture reviews</li>
</ul>
<h2>Requirements</h2>
<ul>
<li>8+ years of software engineering experience</li>
<li>Strong Python and distributed systems background</li>
<li>Excellent communication skills</li>
</ul>
</main>
<footer>Apply via our careers page.</footer>
</body>
</html>
"""


def test_fetch_jd_from_html_extracts_main_content():
    result = fetch_jd_from_html(FIXTURE_HTML)
    assert isinstance(result, dict)
    assert "text" in result
    text = result["text"]
    assert "Senior Engineer" in text
    assert "distributed systems" in text
    assert "Responsibilities" in text
    assert "Requirements" in text


def test_fetch_jd_from_html_omits_boilerplate():
    """The boilerplate header/footer text should be stripped."""
    result = fetch_jd_from_html(FIXTURE_HTML)
    assert len(result["text"]) < len(FIXTURE_HTML)


def test_fetch_jd_from_url_with_file_url(tmp_path):
    html_path = tmp_path / "jd.html"
    html_path.write_text(FIXTURE_HTML, encoding="utf-8")
    url = html_path.as_uri()
    result = fetch_jd_from_url(url)
    assert "Senior Engineer" in result["text"]


def test_fetch_jd_from_url_returns_error_on_bad_url():
    result = fetch_jd_from_url("http://this-domain-does-not-exist.invalid/")
    assert result.get("error") is not None
    assert result.get("text") in (None, "")


def test_fetch_jd_from_html_handles_empty_string():
    result = fetch_jd_from_html("")
    assert result.get("error") is not None
