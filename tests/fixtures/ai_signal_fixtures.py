"""Synthetic text fixtures for the ai_signal_check validator tests.

Each fixture is designed to trigger or avoid a specific finding code:
  - EMDASH_HEAVY_TEXT: trips AI_EMDASH_OVERUSE (HIGH)
  - EMDASH_MILD_TEXT: trips AI_EMDASH_OVERUSE (MEDIUM)
  - OVERUSED_VOCAB_HEAVY_TEXT: 3+ distinct hits -> HIGH
  - OVERUSED_VOCAB_LIGHT_TEXT: 1 hit -> MEDIUM
  - TRICOLON_TEXT: 2+ "X, Y, and Z" clustered -> MEDIUM
  - RHETORICAL_CONTRAST_TEXT: "It's not just X, it's Y" -> HIGH
  - TRANSITIONAL_OVERUSE_TEXT: Furthermore + Moreover + Additionally -> HIGH
  - PRESENT_PARTICIPLE_PILEUP_TEXT: 3+ bullets starting with -ing verbs -> MEDIUM
  - HEDGING_PHRASE_TEXT: "It's worth noting" -> LOW
  - RANGE_QUANTIFIER_TEXT: "ranging from X to Y" -> LOW
  - WHETHER_DISJUNCTION_TEXT: "Whether you're X or Y" -> LOW
  - CLEAN_HUMAN_TEXT: realistic resume bullet with zero AI tells -> score 0
  - HEAVILY_AI_TEXT: kitchen-sink combining 5+ patterns -> score >= 60

No real PII. All synthetic.
"""

EMDASH_HEAVY_TEXT = (
    "Built a distributed system — fast and reliable — for the platform team. "
    "Delivered results — on time, on budget — and exceeded performance targets. "
    "Mentored junior engineers — focused, deliberate work — across two quarters. "
    "Owned the migration — from concept to production — and the post-launch review."
)  # ~50 words, ~8 em-dashes -> HIGH

EMDASH_MILD_TEXT = (
    "Senior engineer with eight years of experience in distributed systems and "
    "platform engineering. Built and maintained services serving 50 million daily "
    "active users — focused on reliability and observability. Mentored four junior "
    "engineers to mid-level. Led incident response across three on-call rotations. "
    "Designed and shipped the company's first internal service-level dashboard. "
    "Worked closely with product to define the platform roadmap for the next two "
    "years. Built deep expertise in OpenTelemetry, Prometheus, and incident "
    "response tooling. Comfortable with ambiguity and self-direction in unstructured "
    "problem spaces."
)  # ~90 words, 1 em-dash -> no em-dash finding (under threshold)

OVERUSED_VOCAB_HEAVY_TEXT = (
    "Passionate about leveraging cutting-edge technology to deliver robust, "
    "scalable solutions. Eager to delve into complex problem spaces and embark "
    "on transformative initiatives that elevate team performance."
)  # delve + leverage + robust + elevate + embark -> HIGH

OVERUSED_VOCAB_LIGHT_TEXT = (
    "Senior software engineer with experience leveraging cloud platforms to "
    "build production systems. Comfortable with on-call work and ambiguity."
)  # 1 hit ("leveraging") -> MEDIUM

TRICOLON_TEXT = (
    "Designed, built, and shipped the platform. "
    "Mentored, coached, and onboarded four engineers. "
    "Tested, deployed, and monitored the migration."
)  # 3 tricolon clusters -> MEDIUM

RHETORICAL_CONTRAST_TEXT = (
    "This is not just a role — it's an opportunity to shape the future. "
    "It's not just about code, it's about culture."
)  # 2 hits -> HIGH

TRANSITIONAL_OVERUSE_TEXT = (
    "I deliver platform engineering work. Furthermore, I focus on reliability. "
    "Moreover, I mentor effectively. Additionally, I write clear documentation. "
    "In conclusion, I bring a comprehensive skill set."
)  # 4 hits -> HIGH

PRESENT_PARTICIPLE_PILEUP_TEXT = (
    "Key responsibilities:\n"
    "- Crafting compelling product narratives.\n"
    "- Leveraging cross-functional partnerships.\n"
    "- Fostering team alignment.\n"
    "- Cultivating data-driven culture.\n"
    "- Driving platform adoption."
)  # 5 bullets starting with -ing verb -> MEDIUM

HEDGING_PHRASE_TEXT = (
    "I led platform engineering at Example Corp. It's worth noting that the "
    "team grew from three to eleven engineers under my tenure."
)  # 1 hit -> LOW

RANGE_QUANTIFIER_TEXT = (
    "Worked on a range of services ranging from internal tooling to "
    "customer-facing APIs spanning the full request lifecycle."
)  # 2 hits ("ranging from", "spanning") -> LOW

WHETHER_DISJUNCTION_TEXT = (
    "Whether you're scaling a startup or modernising legacy infrastructure, "
    "the principles apply."
)  # 1 hit -> LOW

CLEAN_HUMAN_TEXT = (
    "Senior platform engineer. Eight years at three companies, last role "
    "Example Corp (2020-2024). Built the ingestion pipeline serving 50M DAU, "
    "cut p99 latency 40 percent, trained four engineers to mid-level. "
    "Comfortable with on-call and ambiguity. Want to do similar work at a "
    "smaller team where the platform is the product."
)  # Zero AI tells -> score 0

HEAVILY_AI_TEXT = (
    "Passionate senior engineer with a robust skill set, ready to delve into "
    "complex problem spaces. Whether you're scaling a startup or modernising "
    "legacy infrastructure, I bring a comprehensive approach. It's worth noting "
    "that I've led teams ranging from three to fifteen engineers, "
    "leveraging cross-functional partnerships to deliver vibrant, innovative "
    "solutions.\n\n"
    "Key strengths:\n"
    "- Crafting elegant system architectures — robust, scalable, maintainable.\n"
    "- Leveraging modern tooling — observability, automation, infrastructure-as-code.\n"
    "- Fostering team alignment — through clear communication and shared vision.\n"
    "- Cultivating engineering excellence — across the full development lifecycle.\n\n"
    "This isn't just a role, it's an opportunity. Furthermore, the opportunity "
    "extends beyond traditional engineering. Moreover, it represents a chance "
    "to embark on a transformative journey. In conclusion, I'm excited to "
    "elevate this team."
)  # Trips emdash + vocab + present-participle + rhetorical + transitional + hedging + range + whether -> score >= 60
