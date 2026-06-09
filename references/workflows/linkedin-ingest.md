# Workflow: LinkedIn Export Ingestion

**Purpose:** Ingest a LinkedIn ZIP export to seed the create, edit, or tailor workflows with rich user-provided source material. This workflow turns a raw data export into a normalised, confirmed profile that downstream workflows can build from directly.

---

## Trigger Conditions

Start this workflow when any of the following are true:

- The user provides a path to a LinkedIn ZIP export and asks for ingestion.
- The user drops a LinkedIn ZIP into context while asking to create, edit, or tailor a resume — treat ingestion as the first step of that workflow.
- The user says "use my LinkedIn data", "import my LinkedIn export", or any equivalent phrasing.

---

## Inputs

1. **Path to one or more LinkedIn ZIP export files.**
   LinkedIn ships exports under names like `Basic_LinkedInDataExport_*.zip`. Large exports are sometimes split: an initial ZIP arrives immediately and a second-part archive follows within ~24 hours. **Accept multiple paths.** When multiple ZIPs are provided, merge them per step (c) below.

   **Default location:** Place user-supplied ZIPs in `user_data/` at the project root. This directory is gitignored — files placed there are never committed, never logged, and never surfaced outside the current session. The workflow accepts any absolute or relative path; `user_data/` is a convenience convention, not a requirement.

2. **Sections to carry forward (optional, default: all).**
   The user may specify which sections to include — for example, "only positions and skills" or "skip publications". If not specified, all parsed sections are carried forward.

---

## Procedure

**(a) Parse each provided ZIP.**
For each ZIP path, call `scripts/parsers/linkedin_zip.py:parse_linkedin_export(path)`. This function reads the sections the workflow can use (profile, positions, education, skills, certifications, projects, publications, languages) and returns structured data together with a `skipped_files` list.

**(b) Surface the skipped-files list to the user.**
After each parse call, display the `skipped_files` list explicitly. Files that are always excluded include `Connections.csv`, `messages.csv`, `Invitations.csv`, `Reactions.csv`, `Comments.csv`, `Likes.csv`, and related third-party-PII files. **Never hide this list.** The visible skipped-files output is the safeguarding signal — it confirms to the user that the workflow did not read contacts, conversations, or any data belonging to other people.

**(c) Merge parts when multiple ZIPs were provided.**
If the user supplied more than one ZIP:

- **Profile:** take the profile record from whichever part contains `profile.csv`. If both contain one, use the more recently modified file and note the choice.
- **Positions:** concatenate all parts; deduplicate by `(company + title + start date)`.
- **Education:** concatenate all parts; deduplicate by `(school + degree + start date)`.
- **Skills:** concatenate all parts; deduplicate by `name`.
- **Certifications, projects, publications, languages:** concatenate and deduplicate by `name` or the closest equivalent unique key available in each section.

Surface a brief merge summary: how many records each section contained before and after deduplication.

**(d) Present a normalised structured-profile summary for user confirmation.**
Render the merged data as a readable markdown summary — one section at a time or as a single scrollable block depending on length. For each section, ask the user: which roles, skills, certifications, and other entries should carry forward into the downstream workflow?

Apply the **user-veto principle**: anything the user declines or asks to exclude is dropped without argument. Record every inclusion and exclusion decision before proceeding.

**(e) Save the normalised intermediate.**
Write the confirmed profile summary as a BRAINS coaching artifact:

```text
output/linkedin-profile-normalised-YYYY-MM-DD-HHMMSS.md
```

This file carries BRAINS coaching branding — it is an internal session artifact, not a submission-ready document. Include the merge summary from step (c), the full confirmed profile data, and a record of any sections or entries the user excluded.

**(f) Offer the downstream workflow.**
Based on context, offer the most relevant next step:

- **Create** — if the user has no existing resume and wants to build one from the ingested data. The normalised profile replaces the raw interview for the experience, education, and skills sections.
- **Edit** — if the user already has a resume and the ingested data supplements or updates it. Pre-populate the edit workflow with delta entries (roles or credentials not yet on the existing resume).
- **Tailor** — if the user already has a job description in mind and wants to move directly to targeted alignment. Pass the normalised profile into the tailor workflow as the source-of-truth skill and experience set.

If the context is ambiguous, name all three options and ask.

---

## Output Artifacts

| File | Notes |
|---|---|
| `output/linkedin-profile-normalised-YYYY-MM-DD-HHMMSS.md` | BRAINS coaching artifact — intermediate profile; not for submission |

---

## Safeguarding Boundaries

These rules are non-negotiable:

- **The parser skips all third-party-PII files.** `Connections.csv`, `messages.csv`, `Invitations.csv`, `Reactions.csv`, `Comments.csv`, `Likes.csv`, and related files are excluded at the parser level — they are never read, never stored, and never surfaced. See `scripts/parsers/linkedin_zip.py` for the full `SKIP_FILES` set.
- **The skipped-files list is always shown.** Never suppress it, summarise it away, or hide it behind a toggle. It is the primary visible evidence that the workflow respected the safeguarding boundary.
- **Recommend ZIP deletion after parsing.** Once the normalised intermediate is saved, tell the user they can delete the original ZIP — the workflow has what it needs. The skill does not store, copy, or move the original file.
- **User-supplied ZIPs in `user_data/` are gitignored.** They are never committed, never logged in output files, and never referenced by path in any artifact that leaves the local session.
- **The user-veto principle applies to every entry.** No role, skill, certification, or credential is carried forward without the user's explicit confirmation in step (d).
