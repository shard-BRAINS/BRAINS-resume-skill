# BRAINS Resume Skill v1.5.0 — Per-JD folders + traceable artifact UIDs

**Date:** 2026-05-18
**Author:** BRAINS Incubator
**Status:** Approved — ready for plan writing
**Predecessor:** v1.4.1 (maintenance release shipped 2026-05-18)

---

## 1. Goal

Bring order to the skill's file outputs and make every produced document individually traceable. Today the skill emits resumes, cover letters, analyses, and reports into whatever path the caller picks, with no shared organizing convention and no per-file identity beyond an SQLite row id. After v1.5.0:

1. Every job description gets its own folder, named for the role and employer and dated.
2. Every resume and cover letter written by the skill has a deterministic, human-readable filename anchored by the user's name.
3. Every DOCX carries an embedded, invisible-to-Word tracking ID that pins the file to its tracker row regardless of rename, copy, or re-save.

This unblocks downstream features that depend on knowing *which exact document* was sent (efficacy analytics by variant, version-diff reports, "find that resume" search), and turns the outputs directory into a navigable record rather than an undifferentiated dumping ground.

This release **supersedes** the previously-planned v1.5 "disclosure framework polish" — that work moves to v1.6.

## 2. Scope summary

### In scope

1. New package `scripts/outputs/` with three modules:
   - `naming.py` — pure functions for folder names, filenames, sanitization, UID generation.
   - `tagging.py` — DOCX custom-property read/write via `python-docx`.
   - `io.py` — `ensure_jd_folder(jd_id)`, `make_artifact_path(jd_id, kind)`, `finalize_docx(path, jd_id, kind, parent_uid=None)`, `read_artifact_uid(path)`, `find_artifact_by_uid(uid)`.
2. Two new fields on `Profile` (`first_name`, `last_name`) + sidebar UI to set them + first-use modal if missing.
3. Tracker migration `0002_artifact_uids.py`:
   - `resume_versions.artifact_uid TEXT UNIQUE NULL`
   - `resume_versions.parent_uid TEXT NULL`
   - `cover_letters.artifact_uid TEXT UNIQUE NULL`
   - `cover_letters.parent_uid TEXT NULL`
   - `jds.folder_path TEXT NULL`
4. Tracker API extensions:
   - `add_resume_version(...)` and `add_cover_letter(...)` accept optional `artifact_uid` and `parent_uid`.
   - `add_jd(...)` writes the folder path into the new column and creates the folder on disk.
   - New query helper `get_artifact_by_uid(uid) -> Resume | CoverLetter | None`.
5. Generator integration:
   - `resume_to_docx.render_resume_docx(...)` gains optional `artifact_meta: ArtifactMeta` parameter — when present, custom properties are written post-save.
   - `cover_letter_to_docx.render_cover_letter_docx(...)` gains the same.
6. Workflow integration (Streamlit dashboard):
   - `tailor.py`, `cover_letter.py`, `edit.py`, `create.py`, `deai.py`, `check.py` call `io.make_artifact_path(...)` to compute output path before render.
   - `jd_analyze.py` calls `io.ensure_jd_folder(...)` and drops `jd.txt` + `jd-analysis.md` into it.
7. Outputs root: `~/.brains-resume/outputs/` (overridable via `BRAINS_OUTPUTS_DIR`).
8. Slash command reference docs (`references/workflows/*.md`) updated to describe the folder convention so Claude Code handoff scripts route output correctly.
9. Tests: unit coverage for `naming.py` (deterministic), `tagging.py` (round-trip read/write), `io.py` (folder lifecycle + uid issuance), migration upgrade/downgrade, and updated workflow integration tests.
10. Release polish: SKILL.md, README, brand-application, CHANGELOG, claude-project-setup, bundle rebuild, version bump 1.4.1 → 1.5.0, `v1.5.0` tag.

### Out of scope

- Retroactive migration of pre-v1.5.0 files. Existing rows keep `artifact_uid = NULL`. A future `/brains-relocate` command could migrate manually; not in this release.
- A `/brains-scan` rebuild helper that walks the outputs dir to repair tracker links from embedded UIDs. Useful but deferred — listed as future work in §10.
- PDF outputs (`resume_to_pdf`, `cover_letter_to_pdf`). PDFs use ReportLab; embedding a custom property there is a different mechanism and not requested. PDFs in this release keep their existing naming flow and live alongside the DOCX in the same JD folder, sharing the DOCX's UID in their filename only.
- Per-version diff/visualization UI. Tracker now stores `parent_uid` lineage, but rendering it is a later release.
- LinkedIn outputs (`.md` files from `/brains-linkedin-improve`). LinkedIn artifacts aren't JD-anchored and don't get the folder treatment in v1.5.0.
- Multi-user / cloud surfaces. Single-user local skill only.
- Migration of disclosure-framework polish work (moves to v1.6).

## 3. Architecture

### 3.1 Module layout

```text
scripts/
  outputs/                      # NEW PACKAGE
    __init__.py
    naming.py                   # NEW — pure functions
    tagging.py                  # NEW — DOCX custom properties
    io.py                       # NEW — high-level orchestration
  generators/
    resume_to_docx.py           # MODIFIED — optional artifact_meta param
    cover_letter_to_docx.py     # MODIFIED — optional artifact_meta param
    resume_to_pdf.py            # unchanged in this release
    cover_letter_to_pdf.py      # unchanged in this release
  tracker/
    models.py                   # MODIFIED — add artifact_uid, parent_uid, folder_path
    add.py                      # MODIFIED — accept uids in add_resume_version, add_cover_letter
    query.py                    # MODIFIED — new get_artifact_by_uid
    profile.py                  # MODIFIED — first_name + last_name fields
    migrations/
      0002_artifact_uids.py     # NEW
  dashboard/
    sidebar.py                  # MODIFIED — name fields, first-use modal
    workflows/
      tailor.py                 # MODIFIED — uses io.make_artifact_path
      cover_letter.py           # MODIFIED — uses io.make_artifact_path
      edit.py                   # MODIFIED — uses io.make_artifact_path
      create.py                 # MODIFIED — uses io.make_artifact_path
      deai.py                   # MODIFIED — uses io.make_artifact_path
      check.py                  # MODIFIED — uses io.make_artifact_path
      jd_analyze.py             # MODIFIED — uses io.ensure_jd_folder
```

### 3.2 `scripts/outputs/naming.py` — pure functions

```python
CROCKFORD_BASE32 = '23456789ABCDEFGHJKMNPQRSTVWXYZ'  # 30 chars, no 0/O/1/I/L

def new_uid() -> str:
    """Generate a 6-char Crockford base32 UID. ~1B possibilities."""
    return ''.join(secrets.choice(CROCKFORD_BASE32) for _ in range(6))

def slugify(text: str, max_len: int = 40) -> str:
    """Normalize text for folder/filename use.

    - Replaces non-alphanumeric with '-'
    - Normalizes em-dash/en-dash to '-'
    - Drops apostrophes
    - Collapses runs of '-'
    - Strips leading/trailing '-'
    - Truncates to max_len with no trailing dash
    """

def folder_name(
    jd_date: date,
    company: str | None,
    recruiter: str | None,
    role_title: str,
) -> str:
    """Compose 'YYYY-MM-DD_<Anchor>_<Role>'.

    Anchor resolution: company if present, else 'via-<Recruiter>',
    else 'unknown'. Total folder name capped at 80 chars (role
    suffix truncated with '...' if needed).
    """

def artifact_filename(
    first_name: str,
    last_name: str,
    kind: Literal['resume', 'cover-letter'],
    created_date: date,
    uid: str,
    ext: str = 'docx',
) -> str:
    """Compose '<First>_<Last>_<kind>_<YYYY-MM-DD>_<UID>.<ext>'."""

def resolve_folder_collision(parent: Path, candidate_name: str) -> str:
    """If candidate_name exists in parent, return 'name_v2', 'name_v3', ..."""
```

**Why pure functions:** every naming rule is independently testable, deterministic, and free of I/O. Tracker integration and DOCX tagging both consume these — neither owns the rules.

### 3.3 `scripts/outputs/tagging.py` — DOCX custom properties

```python
@dataclass
class ArtifactMeta:
    artifact_uid: str
    artifact_kind: Literal['resume', 'cover-letter']
    jd_id: int | None
    parent_uid: str | None
    created_at: str  # ISO 8601 UTC
    skill_version: str

def write_artifact_meta(docx_path: Path, meta: ArtifactMeta) -> None:
    """Write the meta as DOCX custom properties (docProps/custom.xml)."""

def read_artifact_meta(docx_path: Path) -> ArtifactMeta | None:
    """Read; returns None if no BrainsArtifactId property is present."""
```

Custom property names (all prefixed `Brains` so they're easy to identify and unlikely to collide):

| Property | Type | Example |
|---|---|---|
| `BrainsArtifactId` | string | `KX7M9Q` |
| `BrainsArtifactKind` | string | `resume` |
| `BrainsJDId` | integer | `47` |
| `BrainsParentId` | string \| empty | `PT4N2B` |
| `BrainsCreatedAt` | string | `2026-05-19T10:33:02Z` |
| `BrainsSkillVersion` | string | `1.5.0` |

`python-docx` exposes custom properties via `doc.custom_properties` (added in 0.8.11+; current pin in `pyproject.toml` is 1.1.0, so already supported).

**Invisibility test:** the property does not appear in the body, header, footer, or comment pane. It is visible only via *File → Info → Properties → Advanced Properties → Custom* in Word. The user can delete it from there if they explicitly want to, but no normal editing flow exposes it.

### 3.4 `scripts/outputs/io.py` — orchestration

```python
def ensure_jd_folder(jd_id: int) -> Path:
    """Look up the JD row, compute the folder path via naming.folder_name,
    create it on disk if missing, write the path back to jds.folder_path
    if it was NULL. Returns the folder path."""

def make_artifact_path(
    jd_id: int,
    kind: Literal['resume', 'cover-letter'],
    parent_uid: str | None = None,
) -> tuple[Path, ArtifactMeta]:
    """Reserve a new artifact path + UID. Does NOT write the tracker row
    (caller does that after the generator succeeds). Returns the absolute
    path and a complete ArtifactMeta the generator can pass to
    write_artifact_meta."""

def finalize_docx(path: Path, meta: ArtifactMeta) -> None:
    """Wrap tagging.write_artifact_meta + ensure file exists."""

def read_artifact_uid(path: Path) -> str | None:
    """Convenience: returns just the BrainsArtifactId or None."""

def find_artifact_by_uid(uid: str) -> ResumeVersion | CoverLetter | None:
    """Look up either table by uid."""
```

### 3.5 Data flow — single tailored resume

```text
User triggers /brains-tailor with resume_v17 + jd_42
   │
   ▼
io.ensure_jd_folder(42)                 # creates folder if first artifact for jd_42
   │
   ▼
io.make_artifact_path(42, 'resume', parent_uid='V1XYZ8')
   │  -> (.../2026-05-18_Acme-Corp_Senior-Data-Engineer/
   │          Matthew_Gell_resume_2026-05-19_KX7M9Q.docx, ArtifactMeta(...))
   ▼
LLM produces tailored content (handoff or in-process)
   │
   ▼
resume_to_docx.render_resume_docx(data, path, template, artifact_meta=meta)
   │  - writes the docx
   │  - calls tagging.write_artifact_meta(path, meta) before returning
   ▼
tracker.add_resume_version(
    file_path=path, template=..., focus_areas=...,
    parent_id=17, tagged_jd_id=42,
    artifact_uid='KX7M9Q', parent_uid='V1XYZ8',
)
```

The tracker row is the *last* write; if the generator fails the user is not left with an orphaned row pointing at a missing file.

### 3.6 Migration `0002_artifact_uids.py`

```sql
ALTER TABLE resume_versions ADD COLUMN artifact_uid TEXT;
ALTER TABLE resume_versions ADD COLUMN parent_uid   TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS ux_resume_versions_artifact_uid
  ON resume_versions(artifact_uid) WHERE artifact_uid IS NOT NULL;

ALTER TABLE cover_letters ADD COLUMN artifact_uid TEXT;
ALTER TABLE cover_letters ADD COLUMN parent_uid   TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS ux_cover_letters_artifact_uid
  ON cover_letters(artifact_uid) WHERE artifact_uid IS NOT NULL;

ALTER TABLE jds ADD COLUMN folder_path TEXT;
```

Partial indexes keep `NULL` rows uncovered by the uniqueness constraint, so pre-v1.5.0 rows with `artifact_uid = NULL` don't collide with each other.

Downgrade drops the indexes and columns.

### 3.7 Profile changes

`scripts/tracker/profile.py`:

```python
@dataclass
class Profile:
    focus_areas: list[str] = field(default_factory=list)
    healthy_weekly_rate: int | None = None
    pacing_notes: str | None = None
    log_handoffs: bool = True
    first_name: str | None = None       # NEW
    last_name: str | None = None        # NEW
```

`scripts/dashboard/sidebar.py`:

- Two new text inputs under a "Your name" subsection at the top of the sidebar.
- On dashboard launch, if either is missing, render a one-shot modal (`st.dialog`) asking for them before any workflow tab is enabled.

`io.make_artifact_path` raises `ProfileNameMissingError` if either field is empty; the workflow surfaces this with a friendly message pointing the user at the sidebar.

## 4. Folder & filename rules (canonical reference)

### 4.1 Folder name

`{jd_date}_{anchor}_{role}` where:

- `jd_date`: ISO date the JD row was added (`YYYY-MM-DD`).
- `anchor`: `slugify(company)` if `company` is non-empty, else `via-{slugify(recruiter)}` if recruiter is non-empty, else `unknown`.
- `role`: `slugify(role_title, max_len=40)`.
- Total folder name capped at 80 chars. If over, the role portion is truncated with `...`.
- Collision: `_v2`, `_v3`, ... appended.

### 4.2 Filename

`{first}_{last}_{kind}_{created_date}_{uid}.{ext}` where:

- `first`, `last`: `slugify(profile.first_name)`, `slugify(profile.last_name)`, no internal hyphens (single token each).
- `kind`: `resume` or `cover-letter`.
- `created_date`: ISO date the file was generated (`YYYY-MM-DD`).
- `uid`: 6-char Crockford base32 from `naming.new_uid()`.
- `ext`: `docx` or `pdf`.
- Total filename capped at 100 chars (the user's name and the UID are immutable; role would be the truncation target if a future scheme included it — currently it doesn't, so the cap is informational).

### 4.3 Sanitization rules (`slugify`)

| Input | Output |
|---|---|
| `Senior Data Engineer` | `Senior-Data-Engineer` |
| `R&D / Platform` | `R-D-Platform` |
| `Engineer (Sydney)` | `Engineer-Sydney` |
| `O'Brien & Co.` | `OBrien-Co` |
| `AI/ML — Lead` | `AI-ML-Lead` |
| `Acme   Corp` | `Acme-Corp` |
| `—Acme—` | `Acme` |

Apostrophes dropped; em/en dashes normalized to `-`; runs collapsed; trim.

### 4.4 Examples

| Scenario | Result |
|---|---|
| Hiring company known | `2026-05-18_Acme-Corp_Senior-Data-Engineer/` |
| Recruiter only | `2026-05-18_via-Hays_Senior-Data-Engineer/` |
| Neither | `2026-05-18_unknown_Senior-Data-Engineer/` |
| Second JD same day same company | `2026-05-18_Acme-Corp_Senior-Data-Engineer_v2/` |
| Tailored resume v1 | `Matthew_Gell_resume_2026-05-19_KX7M9Q.docx` |
| Tailored resume v2 | `Matthew_Gell_resume_2026-05-19_PT4N2B.docx` |
| Cover letter | `Matthew_Gell_cover-letter_2026-05-19_H8VR3W.docx` |

## 5. Acceptance criteria

A v1.5.0 build is accepted when **all** of the following are demonstrable:

1. `pytest scripts/outputs/` passes — `naming.py`, `tagging.py`, `io.py` all unit-tested.
2. `pytest scripts/tracker/migrations/` passes — `0002_artifact_uids` upgrade and downgrade are clean on a fresh DB.
3. A fresh `/brains-jd-analyze` run creates a folder at `~/.brains-resume/outputs/<expected>/`, drops `jd.txt` and `jd-analysis.md` in it, and writes the folder path to `jds.folder_path`.
4. A `/brains-tailor` run against an existing JD writes a DOCX at the canonical filename inside the JD folder, the DOCX has the `BrainsArtifactId` custom property readable via `tagging.read_artifact_meta`, and the tracker row has matching `artifact_uid` and `parent_uid`.
5. Renaming the produced DOCX manually does not break `io.find_artifact_by_uid(uid)`.
6. Running `/brains-tailor` twice against the same resume + JD produces two distinct files with two distinct UIDs and `parent_uid` chain reflecting lineage.
7. Opening one of the produced DOCXes in Microsoft Word shows no visible BRAINS markings in the body, header, footer, or comment pane.
8. The sidebar shows `first_name` and `last_name` fields; clearing them and triggering a workflow surfaces `ProfileNameMissingError` with a "set your name in the sidebar" message.
9. CHANGELOG entry exists for v1.5.0 describing per-JD folders + artifact UIDs.
10. `v1.5.0` git tag points at HEAD of `main`.

## 6. Error handling

| Condition | Behavior |
|---|---|
| Profile is missing first or last name | `io.make_artifact_path` raises `ProfileNameMissingError`. Workflow shows a friendly redirect to the sidebar. |
| JD row's `folder_path` is set but folder is missing on disk | `io.ensure_jd_folder` recreates the folder at the stored path. No prompt. |
| JD row's `folder_path` is missing AND on-disk folder for the computed name exists | Adopt the existing folder, write its path into the column. No `_v2` suffix. |
| Filename collision (extremely unlikely — UID collision) | Re-roll the UID up to 5 times; if still colliding, raise `UIDCollisionError`. |
| DOCX write succeeds but custom-property write fails | The DOCX is deleted, an error is raised, the tracker row is not created. All-or-nothing. |
| User edits the DOCX in Word, hits Save, and Word strips the custom property (rare; depends on edition) | Detected on next `read_artifact_meta`. UID still in filename; tracker row still has it. The lineage is preserved through two channels. |
| `BRAINS_OUTPUTS_DIR` points at a non-writable location | First write raises `OutputsDirNotWritableError` with the configured path. |

## 7. Testing strategy

### 7.1 Unit tests (`tests/outputs/`)

- `test_naming.py` — `slugify` cases (the table in §4.3 becomes parametrized assertions), `new_uid` charset + length + uniqueness on 10k samples, `folder_name` for the §4.4 scenarios, `artifact_filename` for the §4.4 scenarios, `resolve_folder_collision` for `_v2`/`_v3`.
- `test_tagging.py` — round-trip write/read of `ArtifactMeta`; verify properties present in `docProps/custom.xml` via direct ZIP read; verify no body text changes vs. an untagged copy.
- `test_io.py` — `ensure_jd_folder` creates dir + writes path; `make_artifact_path` returns unique UID + correct path; `find_artifact_by_uid` finds across both tables; `ProfileNameMissingError` fires when names are unset.

### 7.2 Migration tests (`tests/tracker/migrations/`)

- `test_0002_artifact_uids.py` — apply on a populated v1.4.x DB; verify columns added with NULL defaults; downgrade restores prior schema; reapply is idempotent.

### 7.3 Integration tests (`tests/dashboard/`)

- Extend `test_workflows_card.py` with one scenario per modified workflow: mock the LLM call, assert the file lands at the correct path with correct properties + tracker row.

### 7.4 Smoke

- `tests/test_smoke_outputs.py` — exercise the full chain (`add_jd → ensure_jd_folder → make_artifact_path → render_resume_docx → finalize_docx → add_resume_version`) against a temp `BRAINS_OUTPUTS_DIR`.

## 8. Migration & rollout

- Forward-only. Existing files keep their current paths and names. Pre-v1.5.0 tracker rows have `artifact_uid = NULL` and `parent_uid = NULL`; queries that filter on these handle NULL explicitly.
- Migration `0002_artifact_uids` runs automatically on first dashboard launch (existing migration runner).
- The first-use Profile-name modal blocks workflow tabs but not the dashboard's read-only tabs (Overview, Analytics, Pacing, JDs/Resumes/Cover-Letters/Applications listings) — the user can browse before naming.
- The Settings sidebar gets a clearly-marked "Outputs directory" read-only display of the active root (helps debugging when `BRAINS_OUTPUTS_DIR` is set).

## 9. Documentation updates

- `SKILL.md` — new "File organization" section summarizing the folder + filename convention.
- `references/workflows/tailor.md`, `cover-letter.md`, `edit.md`, `create.md`, `review.md`, `check.md`, `deai.md`, `jd-analyze.md` — updated to reflect that paths come from `io.make_artifact_path`, not the caller.
- `README.md` — outputs directory section.
- `CHANGELOG.md` — v1.5.0 entry.
- `docs/brand-application.md` (if it mentions filenames) — update.
- `claude-project-setup.md` — note the new convention so handoff prompts produce files at the right paths.

## 10. Future work (deferred)

- `/brains-relocate` — opt-in retroactive migration that walks existing files, reads any UIDs present, infers JDs from the tracker, and moves files into the new structure.
- `/brains-scan` — rebuilds path links by walking the outputs dir and reading embedded UIDs. Useful after manual reorganization or restore from backup.
- PDF custom-property embedding via ReportLab (`pdf.setCustomProperty` or similar). Currently PDFs share filename UIDs with their DOCX siblings only.
- Per-variant diff/visualization UI built on the new `parent_uid` lineage.
- LinkedIn Markdown artifacts brought into a parallel organization scheme.
- Disclosure framework polish (originally v1.5 scope; moves to v1.6).

## 11. Open questions / risks

- **Risk: `python-docx` custom property reliability across Word versions.** Mitigation: filename also carries the UID; tracker row is the ultimate source of truth. Property is a *third* read path, not the only one.
- **Risk: very long company names blow the 80-char folder cap.** Mitigation: `slugify(text, max_len=40)` already truncates anchor; total cap then truncates role. Worst case the folder still parses uniquely (date + truncated anchor + truncated role + collision suffix).
- **Open: should the user be able to override the folder name at JD-add time?** Not in this release. Folder name is derived; if the user wants a different anchor they edit the JD's `company` field before the first artifact is written.
- **Open: should `parent_uid` chain be enforced (every variant must have a parent) or optional?** Optional in v1.5.0 — the first-ever variant of a JD has no parent. Forward chains exist when a user iterates.

## 12. References

- Predecessor spec: [docs/specs/2026-05-15-v1-4-0-dashboard-workflows-design.md](docs/specs/2026-05-15-v1-4-0-dashboard-workflows-design.md)
- Tracker schema: [scripts/tracker/migrations/0001_initial_schema.py](scripts/tracker/migrations/0001_initial_schema.py)
- DOCX generators: [scripts/generators/resume_to_docx.py](scripts/generators/resume_to_docx.py), [scripts/generators/cover_letter_to_docx.py](scripts/generators/cover_letter_to_docx.py)
- Profile read/write: [scripts/tracker/profile.py](scripts/tracker/profile.py)
- Sidebar: [scripts/dashboard/sidebar.py](scripts/dashboard/sidebar.py)
- `python-docx` custom properties: https://python-docx.readthedocs.io/en/latest/api/document.html#docx.document.Document.custom_properties
- Crockford base32 spec: https://www.crockford.com/base32.html
