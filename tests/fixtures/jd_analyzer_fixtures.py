"""Synthetic JD text fixtures for the jd_analyzer validator tests.

Each fixture is designed to trigger or avoid a specific finding code:
  - RED_FLAG_HEAVY_JD: trips JD_RED_FLAG_SOFT_CULTURE multiple times → HIGH cluster
  - MASKING_COST_HEAVY_JD: trips JD_MASKING_COST
  - EVIDENCE_OF_FLEX_HEAVY_JD: trips JD_EVIDENCE_OF_FLEX
  - WELL_PARSED_JD: has explicit Required + Nice-to-have headings
  - CLEAN_NEUTRAL_JD: zero red-flag or masking-cost hits
  - MIXED_JD: a realistic-looking JD with some of each
"""


RED_FLAG_HEAVY_JD = """
About the role:
We're looking for a rockstar engineer to join our fast-paced startup. We're
a family here, and we work hard, play hard. You'll wear many hats as a true
ninja-of-all-trades, with a flexible attitude and a can-do mindset.

Responsibilities:
- Be a team player and a go-getter
- Bring passion to everything you do
"""

MASKING_COST_HEAVY_JD = """
About the role:
This is a high-EQ, client-facing role with heavy stakeholder management
responsibilities. You'll be doing client-facing presentations daily in our
open-plan office. The role is phone-heavy with frequent context switching
between accounts.

Responsibilities:
- Manage relationships with C-suite executives
- Present in client meetings
"""

EVIDENCE_OF_FLEX_HEAVY_JD = """
About the role:
We're a remote-first, async-first company with written-comms culture. We
offer flexible hours and accommodations available on request. Our hybrid
policy is 2 days in-office per quarter (not per week).

Parental leave: 26 weeks for primary caregivers, 16 weeks for secondary.
"""

WELL_PARSED_JD = """
About the role:
Senior Platform Engineer focusing on observability and incident response.

Required:
- 5+ years of backend Python experience
- Distributed systems background
- On-call comfort

Nice to have:
- Go experience
- Open-source contributions
- Public speaking at conferences
"""

CLEAN_NEUTRAL_JD = """
About the role:
We are hiring a senior software engineer for our platform team. The role
involves designing and building infrastructure services used across the
company. You will collaborate with product teams and contribute to long-
term technical direction.

Requirements:
- Strong programming skills in Python or Go
- Experience with distributed systems
- Bachelor's degree in Computer Science or equivalent experience
"""

MIXED_JD = """
About the role:
We're looking for a passionate engineer to join our fast-paced team. You
will work in a hybrid setup (2 days per week in-office) and collaborate
asynchronously with global colleagues.

Required:
- Python expertise
- Cloud platform experience

Nice to have:
- Open-source contributions
"""
