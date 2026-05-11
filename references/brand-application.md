# Brand Application Reference

**Purpose:** This document defines when and how BRAINS branding applies to outputs produced by the BRAINS Resume Skill. The coaching report PDF generator (`coaching_report_to_pdf.py`) reads its styling parameters from the specs section below. The `SKILL.md` branding-rules summary draws on this document for its abbreviated guidance.

---

## 1. The Split Rule

Different output surfaces get different brand treatment. The table below is authoritative.

| Surface | Brand treatment | Why |
|---|---|---|
| README, CONTRIBUTING, CHANGELOG | BRAINS parent brand, community-comms tone, Incubator origin credit | These are community-facing project documents — they represent BRAINS Incubator to contributors and users, so the brand applies in full. |
| Skill internal docs (`references/*.md`, `SKILL.md`) | BRAINS parent brand, community-comms tone | Internal references are authored under the BRAINS name and consulted during skill operation; consistent brand treatment reinforces authorship and standards. |
| Generated resumes (DOCX / PDF / text) | **Unbranded** — no BRAINS marks, no footer, no brand colours | The user's professional document. See Section 4. |
| Generated cover letters | **Unbranded** — no BRAINS marks, no footer, no brand colours | Same reason as generated resumes. See Section 4. |
| Coaching reports (markdown + PDF) | **BRAINS branded** — Gold Deep headings, BRAINS mark in header, identity-first language throughout, origin-phrase footer | Coaching reports are authored by the skill on behalf of BRAINS; they are internal or shared coaching artefacts, not employer submissions. |
| Disclosure worksheets | **BRAINS branded** — same treatment as coaching reports, plus BRAINS Trust footer-credit line above the origin-phrase footer | Disclosure content draws on BRAINS Trust safeguarding principles and must acknowledge that provenance. |

---

## 2. Branded Coaching Report — PDF Styling Specs

These parameters are the single source of truth for `coaching_report_to_pdf.py`. Every value must be implemented exactly as written.

### Header

- **Asset:** `assets/brains-mark-light-bg.png`
- **Position:** top-left of page
- **Rendered size:** 1.2 inch width × 0.5 inch height
- **Spacing below header image:** 24 pt

### Body Font

- **Typeface:** Atkinson Hyperlegible Regular
- **Size:** 11 pt
- **Line height:** approximately 1.45 — specified as 16 pt leading in ReportLab

### Heading Fonts

- **h1:** Inter Bold, 18 pt
- **h2:** Inter Bold, 14 pt
- **h3:** Inter Bold, 12 pt

### Colours

- **Heading colour:** Gold Deep `#D99518` on white
- **Body text colour:** `#1A1A1A` on white

### Page Setup

- **Page size:** US Letter
- **Margins:** 0.75 inch on all sides

### Footer (always present on every page)

Verbatim text — do not alter punctuation, capitalisation, or wording:

> `Built by neurodivergent minds, for neurodivergent people.`

Style: 9 pt, grey, centred. **NOT italic.**

### Font-Substitution Fallback

If Atkinson Hyperlegible or Inter are not installed on the build system, fall back to Helvetica (body) and Helvetica-Bold (headings). This is acceptable for v1. The BRAINS rule against italic body text applies regardless of which fonts are active — no italic fallback variants.

---

## 3. Disclosure Worksheet — Additional Footer Credit

Disclosure worksheets receive a BRAINS Trust footer-credit line placed **above** the standard origin-phrase footer on every page.

Verbatim text — do not alter punctuation, capitalisation, or wording:

> `Disclosure guidance developed with BRAINS Trust safeguarding principles.`

Style: 9 pt Atkinson Hyperlegible (or Helvetica fallback), grey, centred. **NOT italic.** Emphasis in this document type is achieved through weight (bold) or position only — never through italics.

Rendering order, bottom of page (top to bottom):

1. BRAINS Trust credit line (disclosure worksheets only)
2. Standard origin-phrase footer

---

## 4. What Never Gets Branded

The following output types must never carry any BRAINS branding — no marks, no brand colours, no footers, no Incubator credit:

- Generated resumes (DOCX, PDF, plain text)
- Generated cover letters
- Any document the user submits to an employer or recruitment process

**Rationale:** Placing BRAINS branding on a document submitted to an employer (a) violates the bias-minimisation goal of the skill, because an unfamiliar logo introduces an unknown variable into screener decisions; (b) implies BRAINS endorsement of the candidate, which is not what is happening; and (c) is generally inappropriate for a professional document the user owns and represents as their own work.

The skill produces these documents as a tool in service of the user. Once produced, they belong to the user alone.
