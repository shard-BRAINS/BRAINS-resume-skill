"""Deterministic ATS-safety checks for a DOCX resume.

Reads the ATS hard rules from ``references/ats-rules.md`` and verifies a DOCX
file conforms to them. Returns a structured result with ``passed`` flag,
``warnings`` and ``failures`` lists.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Union

from docx import Document


@dataclass
class AtsFinding:
    code: str
    message: str


@dataclass
class AtsCheckResult:
    passed: bool
    failures: List[AtsFinding] = field(default_factory=list)
    warnings: List[AtsFinding] = field(default_factory=list)


# Keywords suggesting critical contact info in header/footer.
CRITICAL_INFO_TOKENS = ("@", "+", "phone", "email")


def ats_check(path: Union[str, Path]) -> AtsCheckResult:
    """Run ATS-safety checks on a DOCX resume."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"DOCX not found: {path}")

    doc = Document(str(path))
    failures: List[AtsFinding] = []
    warnings: List[AtsFinding] = []

    # Hard rule: no tables.
    if doc.tables:
        failures.append(AtsFinding(
            code="TABLE_PRESENT",
            message=f"Document contains {len(doc.tables)} table(s). ATS parsers cannot reliably read tables.",
        ))

    # Hard rule: no critical info in headers or footers.
    for section in doc.sections:
        for hf in (section.header, section.footer):
            text = " ".join(p.text for p in hf.paragraphs).strip()
            if text and any(token in text.lower() for token in CRITICAL_INFO_TOKENS):
                failures.append(AtsFinding(
                    code="CRITICAL_INFO_IN_HEADER",
                    message=(
                        f"Header/footer contains contact-like info: {text!r}. "
                        "Many ATS parsers ignore headers and footers — move contact info into the body."
                    ),
                ))

    # Soft rule: text-box / shape presence is harder to detect via python-docx alone.
    # For v0.1 we accept this gap and document it.

    passed = len(failures) == 0
    return AtsCheckResult(passed=passed, failures=failures, warnings=warnings)
