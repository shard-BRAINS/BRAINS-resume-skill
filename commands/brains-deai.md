---
description: Scan resume, cover letter, or LinkedIn text for AI-tell signals and produce a de-AI report with rewrite suggestions
argument-hint: [optional: file path to a .docx/.pdf/.md/.txt file; otherwise paste text in chat]
---

<!-- markdownlint-disable-file MD041 -->
Run the BRAINS Resume Skill AI-signal check. Load `~/.claude/skills/brains-resume/references/ai-signal-patterns.md` for the full pattern catalog and rewrite guidance. Input source: `$ARGUMENTS` (a file path) or pasted text in the next message.

## Procedure

1. **Acquire text.** If a file path is provided, extract text via `scripts/parsers/docx_to_text.py` (DOCX) or `scripts/parsers/pdf_to_text.py` (PDF). If pasted, use as-is. Markdown and plain text use the raw content.

2. **Run the validator.**

```python
from scripts.validators.ai_signal_check import ai_signal_check
result = ai_signal_check(text)
```

1. **Present the report.**

   - Lead with the score: "AI-signal score: {result.score}/100" with the anchor-point interpretation from `references/ai-signal-patterns.md` (0-9 clean, 10-29 mild, 30-49 moderate, 50-79 heavy, 80-100 saturated).
   - For each finding, show the code, severity, excerpt, and suggestion.
   - For each finding code present, link to the matching section in `references/ai-signal-patterns.md` for the full rewrite guidance.

2. **Offer next steps.**

   - If the score is below 10: confirm the text reads as human-authored; no action needed.
   - If 10-29: surface the findings but state that the score is low enough that revision is optional.
   - If 30+: walk the user through the highest-severity findings first, offering rewrite suggestions one at a time. Do not auto-rewrite — the user always chooses.

3. **Output artifact (optional).** If the user requests a saved report, write to `output/deai-report-YYYY-MM-DD-HHMMSS.md` as a BRAINS coaching artifact.

## Safeguarding boundaries

- **The validator scans skill-produced text or user-supplied text.** It is not used as a covert AI-detection tool on third-party content.
- **No auto-rewrite.** Findings are suggestions; the user decides what to change.
- **Lower scores are not a guarantee.** The validator detects pattern density, not authorship; a low score does not certify human authorship to a recruiter using detection tools.
