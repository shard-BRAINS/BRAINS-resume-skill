# Resume Anatomy Reference

## Purpose

This document provides section-by-section guidance on what a good resume looks like, with an ND-aware lens applied to each section. It is the authoritative structural reference for resume work in the BRAINS Resume Skill.

**Scope note:** This is the v1 minimal version. The create-from-scratch and edit workflows shipping in Plan 2 will expand each section with deeper templates, field-level prompting, and tailoring logic. For now, this document establishes the canonical structure and the key considerations per section.

---

## Resume Sections — Canonical Order

A standard chronological resume contains the following sections in this order. **Chronological format is the v1 default** because it performs best across ATS scoring systems and is the format most hiring managers expect.

- **Header** — Name, contact information, and optional links (portfolio, professional profile, location).
- **Summary** (or Objective for early-career candidates) — A 2–4 sentence overview of who you are professionally and what you bring to the role.
- **Experience** — Roles held in reverse-chronological order, each with title, employer, dates, and achievement-focused bullet points.
- **Education** — Degrees, institutions, graduation years, and any notable honours or relevant coursework.
- **Skills** — A concise list of technical competencies, tools, methodologies, or domain expertise.
- **Optional sections** — Projects, Publications, Certifications, Languages, Volunteer. These sections exist and are valid; their full treatment is deferred to Plan 2.

---

## Section Deep-Dives

### Header

**What it must include:**
Your full name (as you want to be addressed professionally), a professional email address, a phone number, and your general location (city and state/country is sufficient — a full street address is not required and not recommended). Include a link to a portfolio or professional profile only if it is current and adds value.

**What it should not include:**
Date of birth, headshot or photo, marital status, national ID numbers, or anything else that invites demographic screening before your qualifications are seen. Do not include a full street address. Do not include social accounts that are personal rather than professional.

**The ND-aware lens:**
Pattern 6 — Direct ND Signal Terms is the primary risk here. Some candidates list diagnostic credentials or community affiliations in their header as a signal of identity. This is a disclosure decision, not a formatting error; see Pattern 6 for the full risk framing and the user-veto principle. Pattern 7 — Indirect ND Signal Terms can also surface if contact links point to ND-community platforms or profiles that imply identity.

**Example — done well:**

```text
Alex Reyes
alex.reyes@example.invalid  |  555-000-1234  |  Portland, OR
portfolio.example.invalid/alexreyes
```

---

### Summary

**What it must include:**
A direct statement of your professional identity (role and domain), your primary area of strength or expertise, and — where possible — a signal of motivation or forward-looking intent. 2–4 sentences. Written in first person.

**What it should not include:**
Empty soft-skills vocabulary — terms like "passionate", "dynamic", "self-starter", or "team player" that label social performance without showing evidence. Do not include diagnostic or clinical language unless the candidate has made an informed disclosure decision. Do not open with a third-person pronoun-free block that sounds like it was written about someone else.

**The ND-aware lens:**
Pattern 1 — Soft-Skills-Coded Vocabulary clusters heavily in summaries; this is the highest-risk section for vague social descriptors that replace concrete evidence. Pattern 8 — Communication-Warmth Deficit is also common here: summaries written to sound "professional" often strip out first-person voice and motivation language entirely, which human screeners read as flat or disengaged. Pattern 6 — Direct ND Signal Terms surfaces when candidates choose to disclose identity in the summary.

**Example — done well:**

```text
I am a data engineer with six years of experience designing and maintaining
large-scale data pipelines. I am drawn to complex data-quality problems and
have a track record of building systems that hold up when data volumes spike.
Most recently I reduced pipeline failure rates by 35% at Example Corp by
re-architecting the ingestion layer.
```

---

### Experience

**What it must include:**
Job title, employer name, employment dates (month and year), and 3–6 achievement-focused bullet points per role. Bullets should lead with an action verb and, where possible, include a measurable outcome. Contract, fixed-term, or project-based context should be noted inline if relevant to explaining duration.

**What it should not include:**
Duty lists that describe responsibilities without outcomes ("Responsible for managing..."). Gap-explanation phrases embedded in the work history ("Career break to..."). Apology language for short tenures or non-linear paths. Pattern 1 buzzwords embedded in bullet points.

**The ND-aware lens:**
Pattern 5 — Modesty / Under-Claim is the dominant risk in experience bullets: hedged language ("contributed to", "helped with", "assisted with") systematically underrepresents solo or candidate-led work. Pattern 3 — Short-Tenure Framing requires attention if two or more consecutive roles each lasted under 18 months without context explaining the duration. Pattern 2 — Employment-Gap Framing is a risk if the candidate has placed explanatory phrases directly inside the work history section. Pattern 4 — Hyperfocus / Narrow-Expertise Framing can surface in experience sections where deep domain work is described without a transferable-skills bridge.

**Example — done well:**

```text
Software Engineer — Example Corp (Mar 2021–Nov 2023)
- Built a real-time event-processing service handling 400k events/day,
  reducing latency by 60% over the prior batch architecture.
- Led migration of three legacy microservices to a containerised deployment
  model, cutting release cycle time from two weeks to two days.
- Wrote and maintained the team's on-call runbook, adopted by two
  additional squads.
```

---

### Education

**What it must include:**
Degree name, institution name, graduation year (or expected graduation year). Honours, awards, or relevant coursework may be included if they add material value for the role being targeted.

**What it should not include:**
GPA unless it is strong and recency makes it relevant (generally within the last three years). High school education once a degree is held. Coursework lists so long they crowd out the experience section. Diagnostic accommodations or IEP / 504 plan history — these are personal records, not resume content.

**The ND-aware lens:**
Pattern 6 — Direct ND Signal Terms can appear here if a candidate lists an accommodation plan, a disability-focused award, or an ND-identity-based scholarship without having made an informed disclosure decision. Pattern 7 — Indirect ND Signal Terms may surface if extracurricular or leadership entries reference ND community organisations. Pattern 2 — Employment-Gap Framing occasionally appears in education sections when candidates explain a delayed graduation or time out of study in apologetic terms.

**Example — done well:**

```text
B.S. Computer Science — Example University, 2019
Relevant coursework: Distributed Systems, Database Internals,
Human-Computer Interaction
Dean's List — Spring 2018, Fall 2018
```

---

### Skills

**What it must include:**
A concise, scannable list of technical competencies, tools, platforms, languages, or methodologies that are accurate, current, and directly relevant to the roles being targeted. Group by category if the list is long (e.g., Languages, Frameworks, Tools, Methodologies).

**What it should not include:**
Self-rated proficiency scales (e.g., "Python ★★★☆☆") — these have no standardised meaning and invite screener assumptions. Soft-skills vocabulary ("excellent communicator", "strong leadership") — these belong in evidence form in the experience section, not as labels in the skills list. Skills listed at a basic or outdated level that the candidate would not want to be tested on.

**The ND-aware lens:**
Pattern 4 — Hyperfocus / Narrow-Expertise Framing is the primary risk in skills sections: a list that is very long in one domain and sparse in others may be accurate but can fail to signal breadth to screeners who default to generalist assumptions. Pattern 1 — Soft-Skills-Coded Vocabulary occasionally appears here when candidates list interpersonal labels alongside technical skills. Pattern 5 — Modesty / Under-Claim surfaces when candidates omit genuine competencies they consider "obvious" or "not impressive enough."

**Example — done well:**

```text
Languages: Python, SQL, Bash
Frameworks & Libraries: FastAPI, dbt, Apache Spark
Infrastructure: Docker, Kubernetes, Terraform
Methodologies: Agile/Scrum, data mesh, test-driven development
```

---

## Closing Note

This reference covers the structural foundation of a well-formed resume through an ND-aware lens. It is intentionally minimal.

**Plan 2 will expand this document** with full create-from-scratch and edit workflow integrations — including field-level prompting for each section, tailoring logic for specific roles and industries, and deeper treatment of the optional sections (Projects, Publications, Certifications, Languages, Volunteer).

Throughout all of that work, the user-veto principle remains absolute: **the skill suggests, the user decides.** Every flag, suggestion, and reframe in the BRAINS Resume Skill is an offer. The candidate's judgment about their own career, identity, and context always overrides the tool's defaults.
