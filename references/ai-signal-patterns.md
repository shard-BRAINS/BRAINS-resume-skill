# AI-Signal Patterns Reference

**Purpose:** Document the nine AI-tell patterns the `ai_signal_check` validator detects, with detection rationale and suggested rewrites. AI-tell signals are increasingly used by recruiters and ATS systems to filter applications; even without detection tools, human reviewers read these patterns as inauthenticity.

The validator surfaces findings as a 0-100 AI-signal score (lower is better). Anchor points:

- **0-9** — clean, no detectable AI tells
- **10-29** — mild traces, almost certainly fine for human review
- **30-49** — moderate AI flavour, worth a rewrite pass
- **50-79** — heavy AI signal, would likely trigger detection tools
- **80-100** — saturated, unambiguously AI-generated to most readers

---

## The nine patterns

### Pattern 1 — `AI_EMDASH_OVERUSE`

**What it detects:** More than 1 em-dash (—) per 200 words of text.

**Why it matters:** Human writers use em-dashes sparingly — typically once per 500 words or fewer. AI models, particularly recent GPT and Claude variants, average 3-5× human em-dash density. Heavy em-dash use is one of the most reliable AI tells.

**Severity:** MEDIUM at moderate overuse; HIGH at heavy overuse.

**Rewrite:** Replace most em-dashes with commas, periods, or parentheses. Reserve em-dashes for genuinely emphatic interruptions, not as a default punctuation choice.

**Example:**

- AI: "Built a system — fast and reliable — for the team. Delivered results — on time — and exceeded targets."
- Human: "Built a fast, reliable system for the team. Delivered results on time and exceeded targets."

### Pattern 2 — `AI_OVERUSED_VOCAB`

**What it detects:** Hits from a curated 18-term AI-lexicon list including delve, tapestry, vibrant, robust, leverage, navigate, embark, elevate, foster, cultivate, harness, myriad, plethora, underscore, showcase, seamless, innovative, comprehensive, holistic.

**Why it matters:** These terms appear in AI-generated text at orders-of-magnitude higher frequency than in human-authored text. They cluster together — a resume using one usually uses several.

**Severity:** MEDIUM on 1-2 distinct hits; HIGH on 3+ distinct hits.

**Rewrite:** Replace with plain alternatives. Specificity beats register.

- `delve` → `look at`, `examine`
- `leverage` → `use`
- `robust` → `reliable`
- `navigate` → `work through`
- `elevate` → `improve`
- `foster` → `support`, `build`
- `seamless` → `smooth`, drop entirely
- `comprehensive` → drop entirely or replace with the specific scope
- `innovative` → describe what is new and specific

### Pattern 3 — `AI_TRICOLON_OVERUSE`

**What it detects:** Two or more "X, Y, and Z" parallel structures clustered within 300 characters of each other.

**Why it matters:** AI loves the three-item parallel structure. Real writing varies: sometimes two items, sometimes four, sometimes a different sentence shape entirely. Repeated tricolons read mechanical.

**Severity:** MEDIUM.

**Rewrite:** Break the rhythm. Use two items where three feels habitual, or rewrite one bullet to a different structure entirely.

### Pattern 4 — `AI_RHETORICAL_CONTRAST`

**What it detects:** "It's not just X — it's Y", "It's not just X, it's Y", "Not only X but also Y", "X isn't just Y, it's Z".

**Why it matters:** This rhetorical move is a strong AI-output signature. Human writing occasionally uses it; AI writing leans on it heavily as a closer or emphasis.

**Severity:** HIGH.

**Rewrite:** Drop the rhetorical setup and state the substantive claim directly.

- AI: "This isn't just a role — it's an opportunity to shape the future."
- Human: "This role would let me shape the platform direction."

### Pattern 5 — `AI_TRANSITIONAL_OVERUSE`

**What it detects:** "Furthermore", "Moreover", "Additionally", "In conclusion" appearing two or more times in the same document.

**Why it matters:** Resume and cover-letter prose almost never needs explicit transition words. Their presence is a strong sign of AI-generated structure with overt scaffolding.

**Severity:** MEDIUM on 2-3 hits; HIGH on 4+ hits.

**Rewrite:** Cut all of them. The reader sees the structure without them.

### Pattern 6 — `AI_PRESENT_PARTICIPLE_PILEUP`

**What it detects:** Three or more consecutive bullets starting with `-ing` verbs (Crafting, Leveraging, Fostering, Cultivating, Driving).

**Why it matters:** AI defaults to gerund-led bullet rhythm. Resume convention is past-tense action verbs (Built, Led, Shipped, Reduced) for completed work, present-tense for current work — not gerunds.

**Severity:** MEDIUM.

**Rewrite:** Convert to past-tense action verbs. `Crafting compelling product narratives` → `Wrote the product narrative that drove the Q3 launch`.

### Pattern 7 — `AI_HEDGING_PHRASE`

**What it detects:** "It's worth noting", "It's important to note", "It should be noted", "It bears mentioning".

**Why it matters:** AI-output filler. Adds no information; signals lack of authorial confidence.

**Severity:** LOW.

**Rewrite:** Cut the phrase. State the claim directly.

- AI: "It's worth noting that the team grew from three to eleven engineers."
- Human: "Grew the team from three to eleven engineers."

### Pattern 8 — `AI_RANGE_QUANTIFIER`

**What it detects:** "ranging from X to Y", "spanning X to Y", "from X all the way to Y".

**Why it matters:** Range quantifiers without specific numeric bounds read AI-vague. Real resumes either give specific numbers or drop the range entirely.

**Severity:** LOW.

**Rewrite:** Replace with the specific numbers, or rewrite to focus on one end of the range.

### Pattern 9 — `AI_WHETHER_DISJUNCTION`

**What it detects:** "Whether you're X or Y", "Whether you need X or Y".

**Why it matters:** Marketing-copy AI-tell. Resume and cover letter prose should address the reader directly, not hypothetically.

**Severity:** LOW.

**Rewrite:** Rewrite to address the actual context directly.

- AI: "Whether you're scaling a startup or modernising legacy infrastructure, the principles apply."
- Human: "The platform-engineering principles I apply to startup-scale problems also work for legacy modernisation."

---

## Severity weights and score

| Severity | Weight | Notes |
|---|---|---|
| HIGH | 20 | Strong AI tell; recruiter-noticeable |
| MEDIUM | 10 | Moderate AI tell; depends on density |
| LOW | 5 | Subtle AI tell; single occurrence is fine in context |

**Score formula:** `min(100, sum(weights))`. Lower is better.

---

## How to use this reference

When the `ai_signal_check` validator surfaces findings, look up each pattern in this document for the rewrite guidance. The validator's per-finding `suggestion` field is a one-line summary; this document holds the full rationale and rewrite examples.
