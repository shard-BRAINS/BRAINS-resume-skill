# ND-Bias Pattern Catalog

## Purpose

This catalog documents ten neurodivergent-bias pattern families commonly found in resumes, cover letters, and related career materials. It is the authoritative reference for bias detection in the BRAINS Resume Skill. Every workflow — review, edit, tailor, cover-letter, create — consults this catalog when scanning submitted documents.

## How to Use

Each pattern family describes a class of language or structural choice that may disadvantage neurodivergent candidates. The catalog is used in two ways:

1. **Deterministic scanning (`bias_scan.py`):** Patterns marked `yes` in the mapping table are detectable by keyword or regex. The validator flags them automatically.
2. **Claude-side contextual review:** Patterns marked `partial` or `yes` in the `Claude-side review required` column need judgment beyond a keyword match. Claude reads context, intent, and document-level signals.

## User-Veto Principle

**The catalog informs — it never enforces. The user always decides.**

When a bias flag is raised, Claude offers the finding and a suggestion. The user may accept, modify, or dismiss the suggestion. This is absolute: no flag is actioned without user consent. Disclosure of neurodivergent identity is a personal decision; this catalog does not push any person to disclose or conceal anything.

---

## Pattern Families

---

### Pattern 1 — Soft-Skills-Coded Vocabulary

**Trigger:** Any of the following words or phrases appear in the document (case-insensitive): `passionate`, `team player`, `great communicator`, `leadership presence`, `thrive in fast-paced environments`, `go-getter`, `self-starter`, `dynamic`, `proactive`, `synergy`, `ninja`, `rockstar`, `guru`, `wear many hats`, `people person`, `culture fit`.

**Why it's biased:** These terms originated as informal social-capital signals favoured by neurotypical workplace cultures. Applicant Tracking Systems trained on high-volume hiring data often treat them as positive signals, but human screeners increasingly dismiss them as filler — creating inconsistent scoring for candidates who use them sincerely. For autistic or ADHD candidates in particular, these vague social-performance terms can replace concrete evidence of skill and make specific, demonstrable competencies invisible to both automated and human review.

**Mitigation:** Replace abstract social descriptors with specific, evidenced claims. Show the behaviour; do not label it.

- **Before:** "A passionate, self-starter team player who thrives in fast-paced environments."
- **After:** "Delivered three production features per sprint across two consecutive quarters while coordinating daily with a cross-functional team of eight."

**User-veto note:** The user always decides whether to retain or replace flagged terms. Some roles and industries still reward this language; the user's judgment on their specific context overrides the flag.

---

### Pattern 2 — Employment-Gap Framing

**Trigger:** Any phrase that explains a gap directly on the resume itself. Specific patterns: `career break to`, `career break for`, `took time off`, `returning to work`, `time away from work`, `period of unemployment`, `sabbatical to focus`, `break to focus on`.

**Why it's biased:** Resume-embedded gap explanations pre-emptively apologise for time that may reflect entirely legitimate life circumstances — including burnout recovery, health management, caregiving, or disability-related periods. Human screeners are documented to penalise visible gaps disproportionately for women and disabled candidates. Explaining the gap on the resume invites scrutiny and signals insecurity before the candidate has had a chance to frame their own story.

**Mitigation:** Remove the explanatory phrase. Use a clean date range and let the cover letter or interview carry any context the candidate chooses to share. If activity during the gap is genuinely relevant, list it as a project or volunteer entry without the apology framing.

- **Before:** "Career break to manage a health condition (2022–2023)."
- **After:** [gap omitted on resume; cover letter opens with current readiness and recent self-directed projects]

**User-veto note:** The user always decides whether to explain a gap, remove it, or reframe it. Some candidates have strong reasons to be transparent; this catalog flags the risk, not the choice.

---

### Pattern 3 — Short-Tenure Framing

**Trigger:** Heuristic — two or more consecutive roles each lasting under 18 months in a chronological work history, without project, contract, or fixed-term context to explain the duration. This is not regex-detectable; it requires date parsing from the resume structure.

**Why it's biased:** Short tenures are disproportionately common in neurodivergent work histories due to sensory mismatch, workplace culture friction, or burnout in under-supported roles. Human screeners apply a "job-hopper" heuristic that has no validity basis for roles under 24 months and systematically disadvantages candidates who needed to exit hostile environments. ATS systems that score tenure continuity amplify this bias at scale before a human even sees the document.

**Mitigation:** Add concise role-type context (contract, fixed-term, project-based) where accurate. Group short related roles under a consulting or portfolio umbrella if applicable. Move emphasis to skills and outcomes rather than tenure length.

- **Before:** "Customer Success Associate — TechCo (Jan 2021–Aug 2021) / Support Lead — AnotherCo (Sep 2021–Mar 2022)"
- **After:** "Customer Success Contractor (2021–2022) — Series of short-term engagements delivering onboarding and tier-1 support across SaaS platforms."

**User-veto note:** The user always decides how to frame tenure. If a role was short for reasons the user does not want to explain, they may choose to leave the chronological listing as-is. The flag is informational.

---

### Pattern 4 — Hyperfocus / Narrow-Expertise Framing

**Trigger:** Heuristic — the same domain-specific token appearing four or more times in close proximity (within approximately 200 words), creating a dense clustering that signals depth without breadth. Example: `PostgreSQL` appearing five times in a 150-word summary without any transferable-skills bridge. This requires contextual proximity analysis, not a simple keyword count.

**Why it's biased:** Hyperfocus is a genuine cognitive strength common in autistic and ADHD candidates, producing deep domain expertise that is often industry-leading. However, a resume that reads as a single-domain monograph fails to signal adaptability to screeners who default to generalist assumptions. Both ATS keyword-matching (which rewards broad vocabulary) and human screeners (who favour "well-rounded" candidates) may score deep specialists lower even when depth is exactly what the role needs.

**Mitigation:** Retain the depth but add a single transferable-skills bridge sentence per section. Map domain expertise to cross-cutting competencies (system thinking, pattern recognition, optimisation under constraints).

- **Before:** "Designed PostgreSQL schemas, wrote PostgreSQL queries, optimised PostgreSQL indexes, and led PostgreSQL migration projects. PostgreSQL performance improved by 60%."
- **After:** "Deep PostgreSQL specialist — designed schemas, wrote complex queries, and led two database migrations. Applied the same systematic optimisation approach to upstream API design and team knowledge-sharing."

**User-veto note:** The user always decides whether to broaden framing. A candidate targeting a narrow specialist role may legitimately want the depth signal dominant.

---

### Pattern 5 — Modesty / Under-Claim

**Trigger:** Passive constructions and credit-sharing language used to describe work that was genuinely solo or candidate-led. Specific patterns: `was part of a team that`, `helped with`, `contributed to`, `assisted with`, `supported the`.

**Why it's biased:** Modesty norms associated with some neurodivergent communication styles, as well as internalised imposter-syndrome patterns common after masking fatigue, lead candidates to systematically downplay their own contributions. Human screeners are documented to read hedged language as evidence of a minor supporting role, regardless of actual impact. ATS systems that rank action-verb strength penalise weak attribution phrases.

**Mitigation:** Replace hedged attribution with direct ownership language. Use active verbs and first-person framing for work the candidate actually led or drove.

- **Before:** "Contributed to the development of a real-time alerting pipeline that reduced incident response time."
- **After:** "Built a real-time alerting pipeline that cut incident response time by 40%."

**User-veto note:** The user always decides how to frame their contributions. Some collaborative cultures genuinely value shared credit language; the user knows their context better than the tool does.

---

### Pattern 6 — Direct ND Signal Terms

**Trigger:** Any of the following terms appear in the document (case-insensitive, whole-word match): `autism`, `autistic`, `ASD`, `Asperger`, `aspie`, `neurodivergent`, `neurodiverse`, `ADHD`, `ADD`, `dyslexia`, `dyspraxia`, `dyscalculia`, `Tourette`, `executive function`, `masking`, `stimming`, `sensory processing`.

**Why it's biased:** Explicit diagnostic or community-identity terms on a resume create a documented disclosure risk. Research consistently shows that disability disclosure during screening reduces callback rates across most industries. The risk is not that disclosure is wrong — it may be exactly right for a candidate — but that most screeners, both human and automated, apply bias when they encounter clinical or community-identity language before the first conversation. ATS systems may also mis-score documents containing medical vocabulary.

**Mitigation:** The flag is not a removal instruction — it is an invitation to a disclosure conversation. If the candidate wants to disclose, suggest moving disclosure to the cover letter or interview, where context and advocacy can accompany the information.

- **Before [resume summary]:** "Autistic software engineer with strong pattern-recognition skills."
- **After [resume summary]:** "Software engineer with exceptionally strong pattern-recognition and systems-thinking skills." [Disclosure moved to cover letter introduction if desired.]

**User-veto note:** The user always decides whether to disclose, where to disclose, and in what terms. Identity-first language is the BRAINS default when disclosure is chosen. This flag never pressures removal.

---

### Pattern 7 — Indirect ND Signal Terms

**Trigger:** Heuristic — presence of language associated with neurodivergent community participation or ND-focused credentials without the candidate explicitly naming a diagnosis. Examples (illustrative, not exhaustive — the list is not complete):

1. Volunteer roles at neurodiversity-affirming employment programmes
2. Participation in autistic-led community events or pride collectives
3. Certifications from neurodiversity-affirming practitioner bodies
4. Involvement with autism community peer-support networks
5. Membership of ADHD coaching and accountability community groups
6. Advisory or ambassador roles for disability-inclusion advocacy organisations
7. References to sensory-friendly workplace design advocacy
8. Involvement in executive-function coaching practice communities
9. Participation in dyslexia-friendly literacy and workplace programmes
10. Employment with ND-specialist staffing or supported-employment services

**Why it's biased:** Indirect signals can identify a candidate as neurodivergent to screeners even without an explicit diagnosis disclosure. Human screeners who hold bias — conscious or not — may infer identity from community affiliations and apply the same callback penalty as direct disclosure. This mechanism — identity inference by association — operates at the human review stage; ATS systems are not typically affected.

**Mitigation:** Reframe involvement language to focus on the skill or outcome rather than the community identity. Retain the experience but lead with what was achieved, not where it was achieved.

- **Before:** "Volunteer Mentor, neurodiversity-affirming employment readiness programme (2022–present)."
- **After:** "Volunteer Career Mentor — coached 12 adults through resume development, interview preparation, and workplace self-advocacy (2022–present)."

**User-veto note:** The user always decides whether to retain, reframe, or remove community affiliations. Affiliation with ND communities is a valid and meaningful part of many candidates' professional identities; the flag is about informed choice, not erasure.

---

### Pattern 8 — Communication-Warmth Deficit

**Trigger:** Heuristic — a summary paragraph or cover letter opening that contains zero first-person pronouns (`I`, `we`, `my`, `our`) AND zero values or motivation tokens (`care`, `believe`, `value`, `love`, `enjoy`, `drawn to`, `motivated`). Both conditions must be present simultaneously to trigger the flag.

**Why it's biased:** Third-person or pronoun-free summary paragraphs are disproportionately common in candidates who have been coached to "sound professional" by excising personal voice — a pattern strongly associated with masking strategies. Human screeners, particularly in roles requiring stakeholder engagement, rate pronoun-free summaries as less memorable and less warm. The absence of motivation language causes screeners to infer lack of passion, compounding the soft-skills vocabulary problem.

**Mitigation:** Reintroduce a single first-person anchor and one motivation signal without resorting to empty buzzwords.

- **Before:** "Experienced product manager with eight years of SaaS delivery experience. Track record of on-time launches and cross-functional alignment."
- **After:** "I am a product manager with eight years of SaaS delivery experience. I am drawn to the full delivery cycle — from shaping ambiguous problems to watching teams ship solutions that hold up in production."

**User-veto note:** The user always decides how much personal voice to include. Some cultures and roles expect formal third-person summaries; the user's read of their target market overrides the default flag.

---

### Pattern 9 — Hyperbole Mismatch

**Trigger:** Heuristic — either (a) the complete absence of any superlative, strength-claim, or enthusiasm signal anywhere in the document, or (b) over-precision in a warmth-signal context. For (b), the specific regex pattern is: decimal-precision percentages (`\d+\.\d+%`) appearing in a resume summary or cover letter opening paragraph — a place where warmth and motivation are expected, not data-table precision.

**Why it's biased:** Both ends of the hyperbole spectrum create screener friction. Flat, uniformly measured language reads as robotic and triggers the warmth-deficit penalty. Hyper-precise metrics in emotional or motivational contexts (a cover letter opening quoting `increased efficiency by 12.7%`) signal social-register mismatch to human screeners even when the data is accurate. ATS systems are not affected, but human screeners in most industries penalise both extremes.

**Mitigation:** Match register to context. Metrics belong in bullet points; warmth and forward-looking intent belong in summaries and opening paragraphs.

- **Before [cover letter opening]:** "I am applying for this role because I increased customer satisfaction scores by 14.3% and reduced churn by 6.2% in my current position."
- **After [cover letter opening]:** "I am applying because I have spent the last three years building the kind of customer relationships where people ask for me by name — and I want to do that at scale."

**User-veto note:** The user always decides the level of precision and tone they want. Technical roles may genuinely reward high precision even in openings; the user's judgment on their audience overrides this flag.

---

### Pattern 10 — Identity-Language Preference

**Trigger:** Mixed person-first and identity-first language appearing in the same document.

- Identity-first terms: `autistic <noun>`, `neurodivergent <noun>`, `disabled <noun>`
- Person-first terms: `person with`, `people with`, `individual with`, `individuals with`

Flag is raised when both styles appear in the same document, signalling inconsistency rather than intentional code-switching.

**Why it's biased:** Language inconsistency signals either uncertainty about community norms or editing by multiple parties with different conventions. Human screeners familiar with disability discourse may read mixed language as lack of self-awareness; screeners unfamiliar with the distinction may find the inconsistency distracting. Neither outcome serves the candidate. BRAINS defaults to identity-first language because it reflects the dominant preference in autistic and many ND communities, but person-first is equally valid when it is the candidate's deliberate choice.

**Mitigation:** Pick one style and apply it consistently throughout the document. BRAINS defaults to identity-first. If the candidate prefers person-first, apply that consistently instead.

- **Before:** "As an autistic professional, I understand the needs of people with disabilities in the workplace."
- **After (identity-first):** "As an autistic professional, I understand the needs of disabled colleagues and neurodivergent workers in the workplace."
- **After (person-first):** "As a person with autism, I understand the needs of people with disabilities in the workplace."

**User-veto note:** The user always decides which language convention to use. The flag points to inconsistency, not to a required choice; the user's preference — identity-first or person-first — is the one that gets applied.

---

## Pattern-to-Validator Mapping

| Pattern # | Pattern Name | Detectable by `bias_scan.py` | Claude-side review required |
|-----------|-------------------------------|------------------------------|------------------------------|
| 1 | Soft-skills-coded vocabulary | yes | no |
| 2 | Employment-gap framing | yes | no |
| 3 | Short-tenure framing | partial | yes |
| 4 | Hyperfocus / narrow-expertise framing | partial | yes |
| 5 | Modesty / under-claim | partial | yes |
| 6 | Direct ND signal terms | yes | no |
| 7 | Indirect ND signal terms | yes | no |
| 8 | Communication-warmth deficit | partial | yes |
| 9 | Hyperbole mismatch | partial | yes |
| 10 | Identity-language preference | yes | no |

**Notes on `partial` entries:**

- Pattern 3 requires date parsing and consecutive-tenure logic beyond simple regex.
- Pattern 4 requires proximity-aware token clustering, not a raw keyword count.
- Pattern 5 flagging is accurate on trigger phrases but requires Claude to confirm the work was genuinely solo or candidate-led before surfacing the flag.
- Pattern 8 requires checking both pronoun absence AND motivation-token absence simultaneously within a bounded paragraph.
- Pattern 9 requires document-section awareness to distinguish summary/opening from body bullet points.

Even where `bias_scan.py` returns `yes`, Claude-side review adds context, calibrates severity, and delivers the finding with appropriate nuance. The validator produces flags; Claude produces a conversation.
