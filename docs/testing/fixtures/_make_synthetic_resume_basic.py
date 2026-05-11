"""Generate a synthetic resume PDF for testing. Run once; commit the resulting PDF.
NO REAL PII — all content is fictional and deliberately innocuous."""
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from pathlib import Path

styles = getSampleStyleSheet()
fixture_path = Path(__file__).parent / "synthetic_resume_basic.pdf"

doc = SimpleDocTemplate(str(fixture_path), pagesize=letter)
story = [
    Paragraph("Alex Test", styles["Title"]),
    Paragraph("alex.test@example.invalid · +0 0000 000000", styles["Normal"]),
    Spacer(1, 12),
    Paragraph("<b>Summary</b>", styles["Heading2"]),
    Paragraph("Software engineer with eight years of experience building data systems.", styles["Normal"]),
    Spacer(1, 12),
    Paragraph("<b>Experience</b>", styles["Heading2"]),
    Paragraph("<b>Senior Engineer</b>, Example Corp · 2020 — Present", styles["Normal"]),
    Paragraph("Built ingestion pipeline processing 50M events daily.", styles["Normal"]),
]
doc.build(story)
print(f"Wrote {fixture_path}")
