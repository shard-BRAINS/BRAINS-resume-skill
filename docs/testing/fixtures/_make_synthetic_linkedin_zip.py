"""Generate a synthetic LinkedIn export ZIP for testing.

Mirrors the LinkedIn data-export structure (as of 2026) with the CSV files
the parser cares about, plus the files the parser must SKIP for
safeguarding reasons. NO REAL PII — all data is fictional.
"""
import io
import zipfile
from pathlib import Path

fixture_path = Path(__file__).parent / "synthetic_linkedin_export.zip"

profile_csv = (
    "First Name,Last Name,Maiden Name,Address,Birth Date,Headline,Summary,Industry,"
    "Zip Code,Geo Location,Twitter Handles,Websites,Instant Messengers\n"
    "Alex,Test,,Example City,1990-01-01,Senior Engineer,"
    "Eight years building data systems.,Information Technology,"
    "0000,Example City Area,,,\n"
)

positions_csv = (
    "Company Name,Title,Description,Location,Started On,Finished On\n"
    "Example Corp,Senior Engineer,Built ingestion pipeline.,Example City,Jan 2020,\n"
    "Sample Industries,Software Engineer,Backend services.,Sample City,Mar 2017,Dec 2019\n"
)

education_csv = (
    "School Name,Start Date,End Date,Notes,Degree Name,Activities\n"
    "Example University,2011,2015,,BSc Computer Science,\n"
)

skills_csv = "Name\nPython\nDistributed Systems\nObservability\nMentoring\n"

certifications_csv = (
    "Name,Authority,Started On,Finished On,License Number\n"
    "ISO 19011 Lead Auditor,Example Standards Body,2021-06-01,,EX-123\n"
)

projects_csv = (
    "Title,Description,Url,Started On,Finished On\n"
    "Open-source observability stack,Personal project,,2019-01-01,2020-06-01\n"
)

publications_csv = (
    "Title,Publisher,Published On,Url,Description,Authors\n"
    "Notes on resilient ingestion,Self-published,2022-09-01,,Article,Alex Test\n"
)

languages_csv = "Name,Proficiency\nEnglish,Native or bilingual proficiency\n"

connections_csv = (
    "First Name,Last Name,URL,Email Address,Company,Position,Connected On\n"
    "Real,Person,https://example.invalid,real@example.invalid,Example Co,Manager,01 Jan 2023\n"
)
messages_csv = (
    "CONVERSATION ID,CONVERSATION TITLE,FROM,SENDER PROFILE URL,TO,DATE,SUBJECT,CONTENT,FOLDER\n"
    "c1,,Real Person,https://example.invalid,Alex Test,2023-01-01,Hi,Hello!,INBOX\n"
)
invitations_csv = (
    "From,To,Sent At,Message,Direction\n"
    "Real Person,Alex Test,2023-01-01,,RECEIVED\n"
)

files = {
    "Profile.csv": profile_csv,
    "Positions.csv": positions_csv,
    "Education.csv": education_csv,
    "Skills.csv": skills_csv,
    "Certifications.csv": certifications_csv,
    "Projects.csv": projects_csv,
    "Publications.csv": publications_csv,
    "Languages.csv": languages_csv,
    "Connections.csv": connections_csv,
    "messages.csv": messages_csv,
    "Invitations.csv": invitations_csv,
}

with zipfile.ZipFile(fixture_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for name, content in files.items():
        zf.writestr(name, content)

print(f"Wrote {fixture_path}")
