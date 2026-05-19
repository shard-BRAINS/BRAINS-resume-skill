"""LLM-backed fact extractor: validation, null-vs-[] semantics, implausibility."""
import pytest


SAMPLE_DOCX_TEXT = """\
Mathilda Gell
Rochedale, QLD  ·  mathilda@malin.com.au  ·  0433814874

Summary
Grade 10 student at Redeemer Lutheran College.

Skills
Customer engagement; Public speaking; Team leadership

Experience
Holiday Work — Faith Christian Distance Education
Brisbane, QLD  ·  January 2026
- Packed enrolment packs for school's intake.

Education
Redeemer Lutheran College — Rochedale, QLD
Grade 10 · Expected completion 2028

Hobbies
Netball, Archery, Tae Kwon Do
"""


VALID_EXTRACTED = {
    "identity": {"name": "Mathilda Gell", "location": "Rochedale, QLD",
                 "email": "mathilda@malin.com.au", "phone": "0433814874"},
    "experience": [{
        "entry_id": "exp-1", "employer": "Faith Christian Distance Education",
        "title": "Holiday Work", "start_date": "2026-01", "end_date": "2026-01",
        "location": "Brisbane, QLD",
        "key_points": ["Packed enrolment packs for school's intake."],
    }],
    "education": [{
        "entry_id": "edu-1", "institution": "Redeemer Lutheran College",
        "qualification": "Grade 10", "completion_year": "2028",
        "completion_status": "expected", "honours": [],
    }],
    "skills": ["Customer engagement", "Public speaking", "Team leadership"],
    "certifications": None,
    "standalone_achievements": None,
    "hobbies": ["Netball", "Archery", "Tae Kwon Do"],
    "languages": None,
    "publications": None,
    "portfolio_links": None,
}


def test_valid_extraction_round_trips(monkeypatch):
    from scripts.drift import extract_facts

    monkeypatch.setattr(extract_facts, "_call_llm",
                        lambda prompt: VALID_EXTRACTED)
    result = extract_facts.extract_facts_from_text(SAMPLE_DOCX_TEXT)
    assert result["identity"]["name"] == "Mathilda Gell"
    assert result["hobbies"] == ["Netball", "Archery", "Tae Kwon Do"]
    assert result["publications"] is None  # not mentioned in source


def test_invalid_extraction_missing_required_key_raises(monkeypatch):
    from scripts.drift import extract_facts

    bad = {k: v for k, v in VALID_EXTRACTED.items() if k != "identity"}
    monkeypatch.setattr(extract_facts, "_call_llm", lambda prompt: bad)
    with pytest.raises(extract_facts.FactExtractionError) as exc:
        extract_facts.extract_facts_from_text(SAMPLE_DOCX_TEXT)
    assert "identity" in str(exc.value)


def test_invalid_extraction_extra_key_raises(monkeypatch):
    from scripts.drift import extract_facts

    bad = {**VALID_EXTRACTED, "secret_field": "nope"}
    monkeypatch.setattr(extract_facts, "_call_llm", lambda prompt: bad)
    with pytest.raises(extract_facts.FactExtractionError):
        extract_facts.extract_facts_from_text(SAMPLE_DOCX_TEXT)


def test_invalid_extraction_wrong_type_raises(monkeypatch):
    from scripts.drift import extract_facts

    bad = {**VALID_EXTRACTED, "skills": "not a list"}
    monkeypatch.setattr(extract_facts, "_call_llm", lambda prompt: bad)
    with pytest.raises(extract_facts.FactExtractionError):
        extract_facts.extract_facts_from_text(SAMPLE_DOCX_TEXT)


def test_flag_implausible_values_catches_placeholders():
    from scripts.drift.extract_facts import flag_implausible_values

    facts = {**VALID_EXTRACTED}
    facts["identity"] = {**facts["identity"], "name": "John Doe"}
    flags = flag_implausible_values(facts)
    assert any("name" in f.lower() and "placeholder" in f.lower() for f in flags)


def test_flag_implausible_values_catches_invalid_dates():
    from scripts.drift.extract_facts import flag_implausible_values

    facts = {**VALID_EXTRACTED}
    facts["experience"] = [{**VALID_EXTRACTED["experience"][0], "start_date": "1899-01"}]
    flags = flag_implausible_values(facts)
    assert any("1899" in f for f in flags)


def test_flag_implausible_values_clean_returns_empty():
    from scripts.drift.extract_facts import flag_implausible_values
    assert flag_implausible_values(VALID_EXTRACTED) == []
