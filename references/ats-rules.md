# ATS Formatting Rules Reference

**Purpose:** Consulted by the ATS check workflow and the bias-aware ATS check workflow. Defines what applicant tracking system (ATS) software can and cannot reliably parse, expressed as concrete rules with reasons. The `ats_check.py` validator implements directly against the hard rules in section 2.

---

## 1. What an ATS is and isn't

An applicant tracking system is, at its core, a parser combined with a keyword scorer. It reads a document the way a computer reads structured data: it extracts text, maps that text to fields (job title, dates, employer, skills), and scores the result against keywords and criteria set by the hiring team. It is not a human reader. It does not interpret intent, recognise nuance, or give credit for creativity of layout. A two-column resume with a custom header font may communicate authority to a person and return empty fields to a machine.

The behaviour of any specific system varies, but the failure modes are consistent. Tables confuse column extraction. Text boxes are often skipped entirely. Headers and footers are treated as metadata containers and many parsers discard them. Non-standard fonts can corrupt character encoding. These are not edge cases; they are well-documented, repeatable problems. The rules below address those failure modes directly.

---

## 2. The hard rules

These rules govern pass/fail ATS parsing. A resume that breaks any of these rules risks having its content extracted incorrectly or not at all.

- **Single-column layout only.** Multi-column layouts cause parsers to read across columns rather than down them, scrambling sentence and date order. All content must flow in a single continuous column.
- **No tables, no text boxes, no shapes containing text.** Content placed inside tables, text boxes, or drawing shapes is frequently skipped or extracted out of order. Every piece of information must sit in the main document body as plain paragraph text.
- **No images carrying critical content.** Names, dates, contact details, and job titles embedded in images or logos cannot be read by a parser. All critical content must appear as selectable, copy-able text.
- **No headers or footers carrying critical content.** Name, contact information, and location placed in the document header or footer are often discarded by parsers. Put this information in the main body, above the first section heading.
- **Standard fonts only.** Use fonts the parser's character-encoding layer reliably handles. Acceptable fonts include: Calibri, Arial, Times New Roman, Helvetica, Georgia, Cambria, and Garamond. Decorative, script, or icon fonts may render as garbled characters or question marks.
- **Body text 10–12 pt.** Text set below 10 pt may be flagged or skipped by some parsers. Text set above 12 pt in the body (not headings) can disrupt line-extraction logic.
- **Standard section headings.** Use conventional heading labels: `Experience`, `Education`, `Skills`, `Summary`, `Certifications`. Non-standard headings such as "Things I have done" or "My toolkit" are not recognised by field-mapping logic and the content beneath them may be miscategorised or lost.
- **Plain `.docx` or `.pdf` only.** Accepted formats are `.docx` (Word-compatible) and text-based `.pdf`. Never submit `.pages`, `.odt`, or scanned image files. Scanned PDFs contain no selectable text and return a blank parse. Some systems reject `.odt` and `.pages` at the upload stage.

---

## 3. The soft rules

These rules do not cause a hard parse failure but will reduce keyword-match scores or introduce date-field errors.

- **Bullet points use simple characters only.** Use `-` (hyphen) or `•` (standard bullet). Decorative dingbats, arrows, or custom symbols may be misread as noise characters, stripping the bullet content from keyword extraction.
- **Date formats: `MMM YYYY` or `MM/YYYY`, consistent throughout.** Mixed formats (some entries as "January 2022", others as "01/22") confuse date-field parsing and can produce incorrect tenure calculations. Pick one format and apply it everywhere.
- **Job titles should match common industry terminology where truthful.** Idiosyncratic internal titles will not match the normalised job-title taxonomies most parsers use for scoring. If your official title differs from the industry-standard equivalent, include both — official title first, common equivalent in parentheses.
- **Keywords from the job description must appear in the resume body as real text.** Place them in sentences and bullet points where they belong. Keywords hidden in invisible whitespace, set in white text on a white background, or embedded at font size 1 are not an effective tactic — see section 4 below.

---

## 4. The dignity rule

Keyword stuffing, white-text-on-white tricks, and font-size-1 hidden text are not only dishonest; they are reliably detected by modern applicant tracking systems. Many systems now flag documents that contain text in a colour matching the background or set below a readable point size, and treat the submission as manipulated. The result is disqualification, not advantage. **The only keyword strategy that works consistently is accurate, specific language placed in the body of the document where it belongs.**

---

## 5. Cross-reference: the ND-specific layer

ATS formatting rules address what a machine can parse. They say nothing about the language patterns that disadvantage neurodivergent candidates at the human-review stage — nor about how standard resume conventions can erase the most relevant strengths of an autistic, ADHDer, or otherwise neurodivergent applicant. That layer is covered separately in [`references/nd-bias-patterns.md`](nd-bias-patterns.md). The two documents are complementary: use this one to ensure a resume clears automated screening, and the other to ensure it reads fairly and accurately to a human reviewer.
