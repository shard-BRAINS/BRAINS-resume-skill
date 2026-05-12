"""Synthetic career-change test fixtures.

Two scenarios, neither involving SAP or any specific real-world technology.
"""

# Scenario A: engineering -> product management
SOURCE_ENG = {
    "summary": "Senior software engineer with eight years of experience building data systems.",
    "experience": (
        "Senior Engineer, Example Corp 2020 - Present\n"
        "Designed and operated the company's primary ingestion pipeline.\n"
        "Mentored four engineers to mid-level.\n\n"
        "Software Engineer, Sample Industries 2017 - 2019\n"
        "Backend services."
    ),
    "skills": "Python, distributed systems, observability, mentoring",
}

TARGET_PM = "product management at a B2B SaaS company"

# Scenario B: education-sector PMO -> public-sector programme delivery
SOURCE_EDU = {
    "summary": "PMO lead at a regional education provider, six years.",
    "experience": (
        "PMO Lead, Example School District 2020 - Present\n"
        "Led district-wide rollout of a new student-information system to 12 schools.\n"
        "Coordinated cross-functional teams of 20+.\n\n"
        "Programme Coordinator, Sample Education 2018 - 2020\n"
        "Curriculum-development project portfolio."
    ),
    "skills": "Programme management, stakeholder coordination, change management, education systems",
}

TARGET_PUBLIC_SECTOR = "regional government programme delivery role"
