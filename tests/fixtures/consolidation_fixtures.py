"""Synthetic resume+LinkedIn position pairs for the consolidation validator.

Each pair is structured data shaped the way the validator expects:
  - resume_positions: list[dict] with company, title, start_date, end_date,
    bullets (list[str]), description (str — for tone analysis).
  - linkedin_positions: same shape.

NO REAL PII. The pairs are designed to trigger each finding code in
consolidation_check.py while a clean pair triggers none.
"""

# --- Clean alignment: same role, same title, same dates, same achievements ---

CLEAN_RESUME = [
    {
        "company": "Example Corp",
        "title": "Senior Engineer",
        "start_date": "2020-03",
        "end_date": "2024-08",
        "bullets": [
            "Led migration of ingestion pipeline to cloud-native platform.",
            "Reduced p99 latency by 40 percent.",
            "Mentored four junior engineers to mid-level.",
        ],
        "description": "Led the migration of the ingestion pipeline to a cloud-native platform serving 50M daily active users. Reduced p99 latency by 40 percent. Mentored four junior engineers.",
    }
]

CLEAN_LINKEDIN = [
    {
        "company": "Example Corp",
        "title": "Senior Engineer",
        "start_date": "2020-03",
        "end_date": "2024-08",
        "bullets": [
            "Led migration of ingestion pipeline to cloud-native platform.",
            "Reduced p99 latency by 40 percent.",
            "Mentored four junior engineers to mid-level.",
        ],
        "description": "Led the migration of the ingestion pipeline to a cloud-native platform serving 50M daily active users. Reduced p99 latency by 40 percent. Mentored four junior engineers.",
    }
]


# --- Job-title mismatch: same employer + overlapping dates, different title ---

TITLE_MISMATCH_RESUME = [
    {
        "company": "Example Corp",
        "title": "Senior Engineer",
        "start_date": "2020-03",
        "end_date": "2024-08",
        "bullets": ["Led platform migration."],
        "description": "Led platform migration.",
    }
]

TITLE_MISMATCH_LINKEDIN = [
    {
        "company": "Example Corp",
        "title": "Engineering Lead",  # different title for same role
        "start_date": "2020-03",
        "end_date": "2024-08",
        "bullets": ["Led platform migration."],
        "description": "Led platform migration.",
    }
]


# --- Date inconsistency: same employer + title, start months differ ---

DATE_MISMATCH_RESUME = [
    {
        "company": "Sample Industries",
        "title": "Software Engineer",
        "start_date": "2017-06",
        "end_date": "2019-11",
        "bullets": ["Backend services for e-commerce."],
        "description": "Backend services for an e-commerce platform.",
    }
]

DATE_MISMATCH_LINKEDIN = [
    {
        "company": "Sample Industries",
        "title": "Software Engineer",
        "start_date": "2017-09",  # 3-month start drift
        "end_date": "2019-11",
        "bullets": ["Backend services for e-commerce."],
        "description": "Backend services for an e-commerce platform.",
    }
]


# --- Achievement only in resume ---

ACHIEVEMENT_RESUME_ONLY_RESUME = [
    {
        "company": "Acme Co",
        "title": "Engineer",
        "start_date": "2015-01",
        "end_date": "2017-05",
        "bullets": [
            "Built shipping calculator service.",
            "Reduced cart-abandonment by 18 percent.",  # only on resume
        ],
        "description": "Built shipping calculator service.",
    }
]

ACHIEVEMENT_RESUME_ONLY_LINKEDIN = [
    {
        "company": "Acme Co",
        "title": "Engineer",
        "start_date": "2015-01",
        "end_date": "2017-05",
        "bullets": ["Built shipping calculator service."],
        "description": "Built shipping calculator service.",
    }
]


# --- Achievement only in LinkedIn ---

ACHIEVEMENT_LINKEDIN_ONLY_RESUME = [
    {
        "company": "Acme Co",
        "title": "Engineer",
        "start_date": "2015-01",
        "end_date": "2017-05",
        "bullets": ["Built shipping calculator service."],
        "description": "Built shipping calculator service.",
    }
]

ACHIEVEMENT_LINKEDIN_ONLY_LINKEDIN = [
    {
        "company": "Acme Co",
        "title": "Engineer",
        "start_date": "2015-01",
        "end_date": "2017-05",
        "bullets": [
            "Built shipping calculator service.",
            "Led architecture review for the platform team.",  # only on LinkedIn
        ],
        "description": "Built shipping calculator service. Led architecture review for the platform team.",
    }
]


# --- Tone divergence: same role, formal vs casual description ---

TONE_DIVERGENT_RESUME = [
    {
        "company": "Example Corp",
        "title": "Senior Engineer",
        "start_date": "2020-03",
        "end_date": "2024-08",
        "bullets": ["Led pipeline migration."],
        "description": (
            "Directed the architectural migration of the ingestion pipeline to a "
            "cloud-native platform, achieving a 40 percent reduction in p99 latency "
            "and a measurable improvement in operator-on-call burden across the "
            "platform-engineering team."
        ),
    }
]

TONE_DIVERGENT_LINKEDIN = [
    {
        "company": "Example Corp",
        "title": "Senior Engineer",
        "start_date": "2020-03",
        "end_date": "2024-08",
        "bullets": ["Led pipeline migration."],
        "description": (
            "Spent four years rebuilding our ingestion pipeline from scratch — turned "
            "out to be a much bigger lift than anyone expected, but we got there. "
            "Made things a lot faster and a lot less painful to operate. Good times."
        ),
    }
]
