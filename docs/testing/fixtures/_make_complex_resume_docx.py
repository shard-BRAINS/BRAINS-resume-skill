"""Generate a synthetic DOCX that exercises section-detection edge cases.

Models real-world section heading patterns:
- Standard Word Heading 1/2 styles
- Bold body paragraphs in larger font that look like headings
- Plain body text headings (matching keyword vocabulary)
- NOT exercising tables / multi-column here — those are separate fixtures.
NO REAL PII.
"""
from pathlib import Path
from docx import Document
from docx.shared import Pt

fixture_path = Path(__file__).parent / "complex_resume_basic.docx"

doc = Document()

doc.add_heading("Alex Test", level=0)
doc.add_paragraph("alex.test@example.invalid | Sample City")

# Summary as plain body text with bold "Summary" header (no heading style)
p = doc.add_paragraph()
run = p.add_run("Summary")
run.bold = True
run.font.size = Pt(14)
doc.add_paragraph("Senior engineer with eight years of experience building data systems.")

# Skills with proper Heading 1 style
doc.add_heading("Skills", level=1)
doc.add_paragraph("Python, distributed systems, observability, mentoring.")

# Experience with proper Heading 1 style
doc.add_heading("Experience", level=1)
doc.add_paragraph("Senior Engineer, Example Corp 2020 - Present")
doc.add_paragraph("Built ingestion pipeline processing 50M events daily.")

# Education as a plain "Education" paragraph (keyword match only, no style)
doc.add_paragraph("Education")
doc.add_paragraph("BSc Computer Science, Example University, 2015")

doc.save(str(fixture_path))
print(f"Wrote {fixture_path}")
