"""Job-description URL fetcher.

Best-effort extraction of job-description text from a URL using trafilatura.
Many job-board sites employ anti-bot protections; this fetcher succeeds on
easy cases (static pages, blog-format JDs, smaller career pages) and
returns a clear error on hard cases. The user-facing fallback is to paste
the JD text directly into the workflow.

Returns a dict with ``text`` (extracted text) and ``error`` (None on success).
"""
from typing import Optional
from urllib.error import URLError
from urllib.request import urlopen
from urllib.parse import urlparse

import trafilatura


def fetch_jd_from_html(html: str) -> dict:
    """Extract job-description text from raw HTML.

    Returns ``{"text": str, "error": None}`` on success, or
    ``{"text": "", "error": "...reason..."}`` on failure.
    """
    if not html or not html.strip():
        return {"text": "", "error": "Empty HTML input."}
    text = trafilatura.extract(html, include_comments=False, include_tables=True)
    if not text:
        return {"text": "", "error": "trafilatura could not extract content from this HTML."}
    return {"text": text, "error": None}


def fetch_jd_from_url(url: str, timeout_seconds: int = 15) -> dict:
    """Fetch a URL and extract job-description text.

    Handles http://, https://, and file:// schemes.
    Returns the same shape as fetch_jd_from_html.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https", "file"):
        return {"text": "", "error": f"Unsupported URL scheme: {parsed.scheme}"}

    try:
        with urlopen(url, timeout=timeout_seconds) as response:
            raw = response.read()
    except URLError as e:
        return {"text": "", "error": f"Could not fetch URL: {e}"}
    except Exception as e:
        return {"text": "", "error": f"Unexpected error fetching URL: {e}"}

    try:
        html = raw.decode("utf-8")
    except UnicodeDecodeError:
        html = raw.decode("latin-1", errors="replace")

    return fetch_jd_from_html(html)
