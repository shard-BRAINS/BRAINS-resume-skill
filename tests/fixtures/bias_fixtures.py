"""Fixture text strings for the bias scanner — one per pattern.

Each fixture is a small piece of synthetic resume text that should
trigger exactly one pattern. NO REAL PII.
"""

PATTERN_1_SOFT_SKILLS = (
    "Passionate self-starter who thrives in fast-paced environments and brings "
    "synergy to every project."
)

PATTERN_2_GAP_EXPLANATION = (
    "2021 — 2022: Career break to focus on personal health and recovery."
)

PATTERN_3_SHORT_TENURES = (
    "Junior Engineer, Company A, Jan 2023 — Aug 2023\n"
    "Associate Engineer, Company B, Sep 2023 — Mar 2024\n"
    "Engineer, Company C, Apr 2024 — Oct 2024"
)

PATTERN_4_HYPERFOCUS = (
    "Deep expertise in PostgreSQL query optimisation, PostgreSQL replication, "
    "PostgreSQL extensions, PostgreSQL internals, PostgreSQL performance tuning."
)

PATTERN_5_UNDER_CLAIM = (
    "Was part of a team that contributed to the redesign. Helped with the migration."
)

PATTERN_6_DIRECT_ND = (
    "Volunteer mentor with Autism Spectrum Society. Active in ADHD advocacy."
)

PATTERN_7_INDIRECT_ND = (
    "Certified Neurodiversity-Affirming Practitioner. Speaker at Autistic Pride conference."
)

PATTERN_8_NO_WARMTH = (
    "Engineer. Eight years experience. Delivered systems. Reduced latency."
)

PATTERN_9_OVER_PRECISION = (
    "Reduced p99 latency by 47.3% over a rolling 14-day window measured at the load balancer."
)

PATTERN_10_MIXED_IDENTITY = (
    "Autistic engineer with a person with ADHD background. Identity-first speaker, "
    "person with disabilities advocate."
)
