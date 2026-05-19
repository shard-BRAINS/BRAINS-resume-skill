"""Transform the workflow's render-time data dict into the Section 4 fact schema.

Pure function, no I/O. Classes the workflow does not capture today (hobbies,
languages, publications, portfolio_links — and inconsistently certifications,
standalone_achievements) are returned as null, NOT empty list, per spec §4.
"""
from __future__ import annotations

import re
from typing import Optional


SCHEMA_VERSION = 1


_EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")
_PHONE_RE = re.compile(r"(?:\+?\d[\d \-()]{7,}\d)")


def _split_contact_line(contact_line: str) -> dict:
    """Parse 'Location  ·  Phone  ·  Email' into identity dict."""
    if not contact_line:
        return {"name": None, "location": None, "phone": None, "email": None}
    # Normalize separator runs (· or | or -) to a single delimiter.
    parts = re.split(r"\s*[·|]\s*", contact_line)
    parts = [p.strip() for p in parts if p.strip()]
    email = None
    phone = None
    location = None
    for p in parts:
        m_email = _EMAIL_RE.search(p)
        if m_email and not email:
            email = m_email.group(0)
            continue
        m_phone = _PHONE_RE.fullmatch(p)
        if m_phone and not phone:
            phone = p
            continue
        if not location:
            location = p
    return {"name": None, "location": location, "phone": phone, "email": email}


_MONTH_MAP = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "jun": "06", "jul": "07", "aug": "08", "sep": "09", "sept": "09",
    "oct": "10", "nov": "11", "dec": "12",
}


def _normalize_date(token: str) -> Optional[str]:
    """Best-effort normalisation to YYYY-MM or YYYY. Returns None on failure."""
    if not token:
        return None
    s = token.strip().lower()
    if s in ("present", "current", "now"):
        return "present"
    m = re.match(r"([a-z]+)\s+(\d{4})$", s)
    if m and m.group(1) in _MONTH_MAP:
        return f"{m.group(2)}-{_MONTH_MAP[m.group(1)]}"
    m = re.match(r"(\d{4})-(\d{1,2})$", s)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}"
    m = re.match(r"(\d{4})$", s)
    if m:
        return s
    return None


def _split_entries(block: str) -> list[list[str]]:
    """Split a multi-entry block into per-entry line lists.

    An entry starts at a non-bullet line followed by a meta line. Bullets
    (lines starting with • or -) belong to the current entry.
    """
    lines = [ln.rstrip() for ln in (block or "").splitlines() if ln.strip()]
    entries: list[list[str]] = []
    current: list[str] = []
    for ln in lines:
        is_bullet = ln.lstrip().startswith(("•", "-"))
        if not is_bullet and current and not current[-1].lstrip().startswith(("•", "-")):
            # Two non-bullet lines in a row — second is the meta line of current entry.
            current.append(ln)
        elif not is_bullet and current:
            # Non-bullet starting a new entry.
            entries.append(current)
            current = [ln]
        else:
            current.append(ln)
    if current:
        entries.append(current)
    return entries


def _parse_experience(block: str) -> list[dict]:
    """Parse an experience block into entry dicts."""
    if not block:
        return []
    entries = _split_entries(block)
    result = []
    for idx, lines in enumerate(entries, start=1):
        head = lines[0].lstrip()
        if "—" in head:
            title_part, employer_part = head.split("—", 1)
        elif " - " in head:
            title_part, employer_part = head.split(" - ", 1)
        else:
            title_part, employer_part = head, ""
        title = title_part.strip()
        employer = employer_part.strip()
        location = None
        start = None
        end = None
        key_points: list[str] = []
        for ln in lines[1:]:
            stripped = ln.lstrip()
            if stripped.startswith(("•", "-")):
                key_points.append(stripped.lstrip("•-").strip())
            else:
                # meta line — look for location · dates
                parts = re.split(r"\s*[·|]\s*", stripped)
                for p in parts:
                    p = p.strip()
                    if not p:
                        continue
                    if re.match(r"^[A-Z][a-zA-Z ]+,\s*[A-Z]{2,3}$", p):
                        location = p
                        continue
                    if re.search(r"[a-z]+\s+\d{4}", p, flags=re.IGNORECASE) or re.match(r"^\d{4}", p):
                        # Date range or single date.
                        if "–" in p or " to " in p.lower() or "-" in p:
                            sep = "–" if "–" in p else (" to " if " to " in p.lower() else "-")
                            left, right = p.split(sep, 1)
                            start = _normalize_date(left)
                            end = _normalize_date(right)
                        else:
                            start = _normalize_date(p)
                            end = start
        result.append({
            "entry_id": f"exp-{idx}",
            "employer": employer or None,
            "title": title or None,
            "start_date": start,
            "end_date": end,
            "location": location,
            "key_points": key_points,
        })
    return result


def _parse_education(block: str) -> list[dict]:
    """Parse an education block into entry dicts.

    Format expected: 'Institution — Location' / meta-line / optional bullets.
    """
    if not block:
        return []
    entries = _split_entries(block)
    result = []
    for idx, lines in enumerate(entries, start=1):
        head = lines[0].lstrip()
        if "—" in head:
            inst_part, _ = head.split("—", 1)
            institution = inst_part.strip()
        elif " - " in head:
            inst_part, _ = head.split(" - ", 1)
            institution = inst_part.strip()
        else:
            institution = head
        qualification = None
        completion_year = None
        completion_status = None
        for ln in lines[1:]:
            stripped = ln.lstrip().lstrip("•-").strip()
            if not stripped:
                continue
            m = re.search(r"(\d{4})", stripped)
            if m:
                completion_year = m.group(1)
            if "expected" in stripped.lower():
                completion_status = "expected"
            elif "currently" in stripped.lower() or "in progress" in stripped.lower():
                completion_status = "in_progress"
            elif "completed" in stripped.lower():
                completion_status = "completed"
            if qualification is None:
                qualification = stripped
        result.append({
            "entry_id": f"edu-{idx}",
            "institution": institution or None,
            "qualification": qualification,
            "completion_year": completion_year,
            "completion_status": completion_status,
            "honours": [],
        })
    return result


def _parse_skills(block: str) -> list[str]:
    """Parse a bullet-or-line skills block into a clean list of strings."""
    if not block:
        return []
    items: list[str] = []
    for ln in block.splitlines():
        stripped = ln.lstrip().lstrip("•-").strip()
        if not stripped:
            continue
        # Drop trailing parenthetical context for matching purposes.
        items.append(stripped.split(" — ", 1)[0].split(" - ", 1)[0].strip())
    return items


def facts_from_workflow_data(data: dict) -> dict:
    """Convert the workflow's render-time data dict into the Section 4 schema.

    For classes the workflow doesn't capture today (hobbies, languages,
    publications, portfolio_links), returns null (NOT empty list) so drift
    compute correctly skips them. Inconsistent classes (certifications,
    standalone_achievements) also return null unless the workflow opts in
    by including them as their own keys.
    """
    identity = _split_contact_line(data.get("candidate_contact_line", ""))
    identity["name"] = data.get("candidate_name") or None

    experience = _parse_experience(data.get("experience", "")) or []
    education = _parse_education(data.get("education", "")) or []
    skills = _parse_skills(data.get("skills", ""))

    return {
        "identity": identity,
        "experience": experience,
        "education": education,
        "skills": skills,
        "certifications": data.get("certifications") if "certifications" in data else None,
        "standalone_achievements": data.get("standalone_achievements") if "standalone_achievements" in data else None,
        "hobbies": data.get("hobbies") if "hobbies" in data else None,
        "languages": data.get("languages") if "languages" in data else None,
        "publications": data.get("publications") if "publications" in data else None,
        "portfolio_links": data.get("portfolio_links") if "portfolio_links" in data else None,
    }
