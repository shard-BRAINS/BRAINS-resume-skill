"""LLM-backed fact extraction for /brains-import.

Calls an LLM with a structured-output prompt, validates the result against
the Section 4 schema, and flags implausible values for user review.

The LLM call is isolated in _call_llm so tests can monkey-patch it. The
production implementation uses anthropic.Anthropic with model selection
read from the BRAINS_DRIFT_EXTRACT_MODEL env var (defaults to claude-haiku-4-5
for cost; can be bumped to sonnet for accuracy).
"""
from __future__ import annotations

import json
import os
import re


class FactExtractionError(Exception):
    """Raised when the LLM returns invalid or unparseable output."""


_EXTRACTION_SYSTEM_PROMPT = """\
You are a structured data extractor. Read the resume text and return a JSON
object matching the BRAINS Resume Skill fact schema v1.

The schema has 10 top-level keys. Each MUST be present. Use null (NOT []) when
the source text doesn't mention the category at all. Use [] only when the
source explicitly states the category is empty (e.g., "Languages: English only"
-> list with one entry; "Languages: none" -> []).

Top-level keys:
- identity: object with {name, location, email, phone}. Use null for missing fields.
- experience: list of {entry_id, employer, title, start_date, end_date, location, key_points}.
  entry_id is "exp-N" numbered from 1. Dates in YYYY or YYYY-MM. key_points is a list of strings.
- education: list of {entry_id, institution, qualification, completion_year, completion_status, honours}.
  completion_status one of "completed", "expected", "in_progress", null.
- skills: list of strings, or null if the source has no skills section.
- certifications: list of {name, issuer, year} or null.
- standalone_achievements: list of strings (e.g. awards, recognitions) or null.
- hobbies: list of strings or null.
- languages: list of {language, proficiency} where proficiency is one of
  "native", "fluent", "professional", "conversational", "basic". Or null.
- publications: list of {title, venue, year, authors, url} or null.
  authors is a list of strings.
- portfolio_links: list of {label, url} or null.

Output ONLY the JSON object. No prose.
"""


_REQUIRED_KEYS = (
    "identity", "experience", "education", "skills",
    "certifications", "standalone_achievements", "hobbies",
    "languages", "publications", "portfolio_links",
)


def _call_llm(prompt: str) -> dict:
    """Make the actual Anthropic API call. Monkeypatched in tests.

    Returns the parsed JSON dict. Raises FactExtractionError on parse failure.
    """
    try:
        import anthropic
    except ImportError as e:
        raise FactExtractionError(f"anthropic SDK not installed: {e}")
    client = anthropic.Anthropic()
    model = os.environ.get("BRAINS_DRIFT_EXTRACT_MODEL", "claude-haiku-4-5-20251001")
    resp = client.messages.create(
        model=model,
        max_tokens=4096,
        system=_EXTRACTION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text if resp.content else ""
    # Strip code fences if the model wrapped output.
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise FactExtractionError(f"LLM returned non-JSON output: {e}") from e


def _validate_schema(data: dict) -> None:
    """Strict shape validation. Raises FactExtractionError on any issue."""
    if not isinstance(data, dict):
        raise FactExtractionError("Expected top-level JSON object")
    missing = [k for k in _REQUIRED_KEYS if k not in data]
    if missing:
        raise FactExtractionError(f"Missing required keys: {missing}")
    extra = [k for k in data if k not in _REQUIRED_KEYS]
    if extra:
        raise FactExtractionError(f"Unexpected keys: {extra}")
    # Type checks.
    if data["identity"] is not None and not isinstance(data["identity"], dict):
        raise FactExtractionError("identity must be object or null")
    for k in ("experience", "education", "skills", "certifications",
              "standalone_achievements", "hobbies", "languages",
              "publications", "portfolio_links"):
        if data[k] is not None and not isinstance(data[k], list):
            raise FactExtractionError(f"{k} must be list or null, got {type(data[k]).__name__}")


_PLACEHOLDER_NAMES = {"john doe", "jane doe", "first last", "your name",
                      "fullname", "name here", "<name>"}
_PLACEHOLDER_EMAILS = {"example@example.com", "user@example.com",
                       "your.email@example.com", "<email>"}


def _looks_like_placeholder(value: str | None, vocab: set[str]) -> bool:
    if not value:
        return False
    return value.strip().lower() in vocab or "<" in value or "{{" in value


def flag_implausible_values(facts: dict) -> list[str]:
    """Return a list of human-readable warnings about likely-placeholder values.

    Used as a soft warning surface in the /brains-import workflow card.
    """
    flags: list[str] = []
    identity = facts.get("identity") or {}
    if _looks_like_placeholder(identity.get("name"), _PLACEHOLDER_NAMES):
        flags.append(
            f"identity.name looks like a placeholder: {identity.get('name')!r}"
        )
    if _looks_like_placeholder(identity.get("email"), _PLACEHOLDER_EMAILS):
        flags.append(
            f"identity.email looks like a placeholder: {identity.get('email')!r}"
        )
    # Experience / education dates outside [1900, 2100].
    for entry in (facts.get("experience") or []):
        for f in ("start_date", "end_date"):
            v = entry.get(f) or ""
            m = re.match(r"^(\d{4})", v)
            if m:
                year = int(m.group(1))
                if year < 1900 or year > 2100:
                    flags.append(
                        f"experience entry {entry.get('entry_id')!r} {f}={v!r} - year 1899 (looks suspicious)"
                        if year == 1899 else
                        f"experience entry {entry.get('entry_id')!r} {f}={v!r} - implausible year"
                    )
    return flags


def extract_facts_from_text(text: str) -> dict:
    """Extract a Section 4 fact dict from raw resume text via LLM.

    Validates strictly. Raises FactExtractionError on any failure.
    """
    if not text or not text.strip():
        raise FactExtractionError("Empty input text")
    data = _call_llm(text)
    _validate_schema(data)
    return data
