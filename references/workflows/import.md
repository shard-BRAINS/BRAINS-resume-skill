# Workflow: Import an Existing Resume as a Baseline

**Purpose:** Take an existing resume — a DOCX the user already has, or plain text they paste — and register it as a candidate's **baseline** version. The workflow runs the LLM-backed fact extractor over the source, surfaces any implausible values for review, and on confirmation writes a `resume_versions` row plus a fact snapshot and drift scores. The imported baseline becomes the reference point that later drift comparisons measure against.

---

## Trigger Conditions

Start this workflow when any of the following are true:

- The user explicitly asks to import, ingest, or add an existing resume as a baseline.
- The user has a finished resume produced outside the skill and wants drift tracking to start from it.
- The user wants a candidate's first tracked version to be their current real-world document rather than one built via `/brains-create`.
- The user is setting up drift analytics for someone else and supplies that person's existing resume.

This is not the right workflow when the user wants to build a resume from scratch (use `/brains-create`) or revise one already tracked (use `/brains-edit`).

---

## Inputs

1. **Source text (required).**
   The plain-text content of the resume. If the user has a DOCX, they paste its text content into the workflow. The original DOCX file is **not** stored or copied — only the extracted facts are persisted.

2. **For candidate (optional).**
   The full name of the person the resume belongs to (e.g. "Mathilda Gell"). Leave blank when importing the profile holder's own resume. When provided, the name is split into first/last for filename construction and stamped onto the artifact metadata and the tracker row so both record who the artifact is FOR. When omitted, the profile name is used; if the profile has no first/last name set, the workflow surfaces an error asking the user to set it or provide a candidate name.

---

## Procedure

**(a) Extract facts from the source text.**
Call `scripts/drift/extract_facts.py:extract_facts_from_text(source_text)`. This runs the LLM extractor with a structured-output prompt and validates the result against the Section 4 fact schema (10 top-level keys: identity, experience, education, skills, certifications, standalone_achievements, hobbies, languages, publications, portfolio_links). Categories absent from the source are captured as `null`; categories the source explicitly states are empty are captured as `[]`.

**(b) Surface schema-validation failures.**
If the extractor raises `FactExtractionError` — non-JSON output, missing or unexpected keys, wrong types — the workflow stops and reports the error to the user. Validation failures are hard stops; the import does not proceed.

**(c) Flag implausible values.**
Run `flag_implausible_values(facts)` over the extracted facts. This produces soft warnings for likely-placeholder content — placeholder names ("John Doe", "Your Name", `<name>`), placeholder emails, and experience dates outside a sane year range. Implausibility flags are **soft**: they do not block the import, they prompt review.

**(d) Confirm before committing when warnings exist.**
If `flag_implausible_values` returned any warnings and the user has not confirmed, the workflow returns `needs_confirmation` and displays the warnings. The user reviews them and either fixes the source and re-imports, or explicitly confirms ("import anyway"). On confirmation the workflow proceeds. When there are no warnings, the import proceeds directly.

**(e) Write the row, snapshot, and drift scores.**
On commit the workflow:
- Computes the output path in `_library/` and an `ArtifactMeta` via `_resolve_target`.
- Calls `scripts/tracker/add.py:add_resume_version(...)` with `template="imported"` and `for_candidate` set. Because this is the first non-archived row for the candidate, the auto-baseline logic sets `is_baseline=1`.
- Calls `scripts/drift/compute.py:write_snapshot_and_compute_drift(artifact_uid, facts)` to persist the fact snapshot and the drift-score row.

---

## Output Artifacts

This workflow does not render a DOCX or PDF — it ingests one. It produces database rows only:

| Row | Notes |
|---|---|
| `resume_versions` | One row. `template="imported"`, `is_baseline=1` (auto — first row for the candidate), `for_candidate` set when an explicit name was given. `file_path` points at a `_library/` path; no file is written there. |
| `resume_fact_snapshots` | One row. The extracted Section 4 fact dict, `schema_version=1`. |
| `resume_drift_scores` | One row. Both `vs_parent_score` and `vs_baseline_score` are NULL — a baseline has no parent and is not measured against itself. |

---

## Boundaries and User Agency

These rules are non-negotiable:

- **The original DOCX is not stored.** Only the extracted facts are persisted. The user keeps their own copy of the source document; the skill never copies, moves, or archives it.
- **Schema-validation failures surface to the user.** When the LLM returns output that fails strict schema validation, the workflow stops and reports the error rather than guessing or repairing the data silently.
- **Implausibility flags are soft.** Placeholder-name, placeholder-email, and out-of-range-date warnings prompt review; they never block an import on their own. The user can confirm and proceed.
- **Confirmation is required to override warnings.** When warnings exist, the import does not commit until the user explicitly confirms. The user-veto principle runs both ways here — the user may also decline and fix the source instead.
- **All ten fact classes are captured when present.** `hobbies`, `languages`, `publications`, and `portfolio_links` are extracted alongside the core classes whenever the source mentions them, so the imported baseline is a complete snapshot for later drift comparison.
- **The imported baseline is the new reference point.** Once committed it is the active baseline for that candidate; subsequent versions measure drift against it.
