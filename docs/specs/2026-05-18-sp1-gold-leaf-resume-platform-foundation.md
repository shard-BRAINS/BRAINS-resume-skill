# Gold Leaf Resume — SP1: Platform Foundation design

**Date:** 2026-05-18
**Author:** BRAINS Incubator
**Product:** Gold Leaf Resume (a shard product under BRAINS Incubator)
**Status:** In implementation — SP1·M0 + M1 + M2 complete (2026-05-18 — `sp1-m0`, `sp1-m1`, `sp1-m2` tags in `gold-leaf-resume`); M3 (Frontend auth + consent flows) next.
**Predecessor:** BRAINS Resume Skill v1.4.1 (local Streamlit + Claude Code, shipped 2026-05-18)

---

## 1. Goal

Stand up the multi-tenant, AU-resident SaaS skeleton — Gold Leaf Resume — that every subsequent sub-project (SP2 Resumes vertical → SP7 Launch) builds on. SP1 is intentionally pre-feature: no resume review, no tailoring, no LLM workflow runs. What ships is the foundation: accounts, auth, consent, file storage, database, LLM provider abstraction with usage caps, the empty object-first UI shell, and the data model that lets billing drop in later without rework.

The acceptance test for SP1: a new user can sign up at `goldleafresume.<tld>`, verify their email, accept consent, see an empty dashboard with all the right tabs, change their profile, export their (empty) data, and delete their account — and every part of that flow is logged, metered, and AU-resident.

## 2. Scope summary

### In scope

1. Monorepo with `apps/web` (Next.js 15) + `apps/api` (FastAPI) + shared packages.
2. Supabase project in `ap-southeast-2` (Sydney) — Auth + Postgres + Storage.
3. Auth flows: signup (email/password, magic link, Google OAuth), email verification, consent gating, password reset, email change, account deletion (30-day pending window).
4. Empty object-first dashboard shell at `/app/*` — Resumes, JDs, Cover Letters, Applications, Analytics, Pacing, Settings tabs. Settings is fully functional in SP1; the rest are empty "coming soon" placeholders.
5. Postgres schema covering identity/tenancy, billing-readiness, consent, audit, usage metering, the encrypted BYO-key vault, and the object tables (defined but empty) that SP2–SP5 populate.
6. LLM provider abstraction via LiteLLM with pre-call quota check + post-call usage-event writes. Default provider Anthropic Claude. No actual LLM workflow runs from SP1.
7. Encrypted BYO LLM key storage (schema + helpers; no UI surface).
8. File storage via Supabase Storage (Sydney), signed-URL upload/download, per-account RLS, `sensitive_data` flag.
9. Consent + data-rights primitives wired end-to-end: T&Cs, privacy policy, AU sensitive-data consent (required), marketing email (optional). Revocation + data export + delete-my-account all functional.
10. Audit log (`audit_log`) + consent log (`consent_records`) — append-only.
11. Sentry frontend + backend; structured JSON logging; `/healthz` + `/readyz` endpoints.
12. CI/CD: GitHub Actions for lint/typecheck/test/migration-check on PR; auto-deploy to Fly + Vercel on `main`; manual migration trigger.
13. Three environments: `local`, `staging`, `production` — all `ap-southeast-2`.
14. Stripe-readiness: `plans` / `subscriptions` / `billing_events` schema seeded with a single `free` plan; webhook receiver scaffolded at `/webhooks/stripe` returning HTTP 501; `@require_plan` middleware decorator in place but no-op against free.
15. Public legal pages: `/legal/terms`, `/legal/privacy`, `/legal/cookies`. Content stub-quality in SP1, polished in SP7.

### Out of scope

- Any actual LLM workflow (Review, Tailor, Edit, Cover letter, etc.) — those land in SP2+.
- Stripe charges, paid plans, plan upgrades, billing portal — post-v1.
- BYO LLM key UI (the encrypt/decrypt helpers + schema land in SP1; the user-facing key-management page lands when needed, likely SP3 or SP6).
- Marketing landing page polish, hero copy, screenshots, testimonials — SP7.
- Public help / docs / changelog site — SP7.
- LinkedIn ZIP ingest, resume↔LinkedIn consolidation — SP5.
- The always-on AI assistant sidebar — SP6.
- Multi-region (UK + US) — post-v1.
- Coach tier (multi-user accounts) — the `account_users` table is provisioned but only ever has one owner per account in SP1.
- Mobile native apps — post-v1.
- Hard purge of sensitive data on consent revoke (vs. flagged-inaccessible) — SP7 refinement.
- Apple Sign-In, passkeys, SAML/SSO for organisations — post-v1.
- Sentry session replay, OpenTelemetry traces, Prometheus/Datadog metrics — post-SP2.
- Cooperative editing, sharing, public profile links — post-v1.
- A public REST API for third-party developers — explicitly excluded from the SaaS scope per user input ("non-API for now").

## 3. Where SP1 sits in the roadmap

The full cloud-product effort decomposes into seven sub-projects (Approach C — Hybrid):

| # | Sub-project | Status |
|---|---|---|
| **SP1** | **Platform foundation** (this spec) | In planning |
| SP2 | Resumes vertical — Review, Edit, Create, De-AI, Final check | Future |
| SP3 | JDs + Tailor + Cover letter vertical | Future |
| SP4 | Application loop vertical — Tracker, Precheck, Disclosure | Future |
| SP5 | LinkedIn vertical — Ingest, Improve, Consolidate, Career-change | Future |
| SP6 | AI assistant overlay (always-available sidebar, tool-calling across SP2–SP5) | Future |
| SP7 | Launch readiness — marketing, polish, accessibility audit, Stripe rollout | Future |

Every sub-project gets its own spec → plan → implementation cycle. This document is the SP1 spec only.

## 4. Architecture

### 4.1 Topology

```
                                    ┌─────────────────────────────┐
                                    │  Vercel (Sydney edge cache) │
                                    │   apps/web (Next.js 15)     │
                                    └──────────┬──────────────────┘
                                               │
                                               │  HTTPS, Supabase JWT in Bearer
                                               ▼
                                    ┌─────────────────────────────┐
                                    │  Fly.io (syd region)        │
                                    │   apps/api (FastAPI)        │
                                    └──┬─────────────┬────────────┘
                                       │             │
                       Service-role key│             │ Resend SDK (email)
                                       ▼             ▼
                ┌──────────────────────────────┐ ┌──────────────┐
                │  Supabase (ap-southeast-2)   │ │  Resend      │
                │   Auth + Postgres + Storage  │ │  (US-region; │
                │                              │ │   no PII in  │
                │                              │ │   bodies)    │
                └──────────────────────────────┘ └──────────────┘
                                       │
                                       │ outbound only
                                       ▼
                ┌──────────────────────────────┐
                │  LLM providers via LiteLLM   │
                │   (Anthropic default;        │
                │    not called in SP1)        │
                └──────────────────────────────┘
```

Data residency: user identity + profile data + uploaded files + every account-scoped row in Postgres live in `ap-southeast-2`. Sentry events scrub PII before egress. Resend is used for transactional email only — message bodies contain no resume content, no JD content, no disclosure data. LLM provider egress is not exercised in SP1.

### 4.2 Frontend — `apps/web`

**Stack:** Next.js 15 (App Router) · TypeScript strict · Tailwind CSS · shadcn/ui · `@supabase/ssr` for SSR-aware Supabase client · `@tanstack/react-query` for server state · `openapi-typescript-codegen` for typed FastAPI client.

**Hosting:** Vercel. Sydney edge for static assets; SSR functions in Vercel's global pool (acceptable cold-start latency for SP1; revisit at SP7 if measured latency causes UX issues).

**Auth integration:** Supabase Auth via `@supabase/ssr`. Session cookies are httpOnly. Server components verify the JWT; client components rely on the Supabase JS client's auth state subscription.

**Calling FastAPI:** every authenticated request includes the Supabase access token as `Authorization: Bearer <jwt>`. The typed client is generated at build time from FastAPI's OpenAPI schema. The frontend never holds the Supabase service-role key.

**Routes:**

```
/                       Marketing-light landing (SP1: minimal — name, one-paragraph blurb,
                        "Sign in / Sign up" CTAs, BRAINS Incubator attribution). SP7 polishes.
/signup
/login
/verify                 (email verification landing — handles Supabase callback)
/reset-password
/accept-consent         (mandatory after first verify; before any /app route)
/legal/terms
/legal/privacy
/legal/cookies

/app                    Authenticated shell layout (sidebar + content area).
  /app/dashboard        Overview placeholder ("SP2 will populate this")
  /app/resumes          empty placeholder
  /app/jds              empty placeholder
  /app/cover-letters    empty placeholder
  /app/applications     empty placeholder
  /app/analytics        empty placeholder
  /app/pacing           empty placeholder
  /app/settings         FULLY FUNCTIONAL — profile, account, data rights, audit log
```

**Sidebar navigation (carries the journey-stage thinking from the v1.4.1 Workflows tab):**

- **1 · Apply** — Applications, JDs
- **2 · Build** — Resumes, Cover Letters
- **3 · Track** — Analytics, Pacing
- **Settings** (bottom)

For SP1, all section-1/2/3 links route to empty placeholder pages.

**Accessibility baseline (commitment from day 1):** WCAG 2.1 AA. Keyboard navigation, visible focus rings, `prefers-reduced-motion` honoured, semantic landmarks (`<header> <nav> <main> <aside>`), real heading hierarchy, alt text discipline, colour-contrast tokens that pass at all gold-on-* combinations. Formal audit deferred to SP7; informal self-review at each PR.

**Styling tokens (Gold Leaf palette — defined in `packages/design-tokens`):**

- `goldleaf.50–900` (warm gold scale; primary brand)
- `cream.50–200` (ivory neutrals for light backgrounds)
- `ink.700–950` (deep neutral text; dark-mode primary)
- `brains.blue` (parent-brand accent used only in footers / "by BRAINS Incubator")
- Semantic tokens: `bg-surface`, `bg-elevated`, `fg-default`, `fg-muted`, `border-default`, `accent`, `danger`, `success`.

Dark mode is opt-in via OS preference; the dashboard defaults to dark in line with the existing Streamlit dashboard.

### 4.3 Backend — `apps/api`

**Stack:** FastAPI · Pydantic v2 · uvicorn · SQLAlchemy 2 · Alembic · httpx · LiteLLM · structlog · `cryptography` (Fernet for vault). Python 3.12.

**Hosting:** Fly.io. Primary region `syd`. Minimum 2 machines for HA, shared-cpu-1x sized for SP1 traffic (~$10/mo). Hostname `api.goldleafresume.<tld>`.

**Module layout:**

```
apps/api/
  src/
    main.py                  # FastAPI app factory, lifespan, route mounting
    config.py                # Pydantic Settings (env-driven)
    deps.py                  # FastAPI dependencies — auth user, db session, account
    middleware/
      auth.py                # verify Supabase JWT via JWKS
      request_id.py          # correlation IDs, ContextVar
      usage_cap.py           # pre-LLM-call quota check
      consent_gate.py        # block routes if mandatory consent missing
    routes/
      v1/
        me.py                # GET /v1/me, PATCH /v1/me, DELETE /v1/me
        profile.py           # GET/PATCH /v1/me/profile
        consent.py           # POST /v1/me/consent, GET /v1/me/consent/log
        usage.py             # GET /v1/me/usage
        files.py             # POST /v1/files (signed-URL issuer), GET /v1/files/:id
        export.py            # POST /v1/me/export (kicks off ZIP build)
        audit.py             # GET /v1/me/audit (read-only audit log)
      webhooks/
        stripe.py            # HTTP 501 in SP1, scaffolded for billing rollout
    services/
      llm/                   # LiteLLM wrapper, model routing, metering hooks
      vault/                 # encrypted BYO key store (Fernet + HKDF per-row)
      storage/               # Supabase Storage helpers, signed-URL issuance
      email/                 # Resend wrapper + template renderer
      audit/                 # audit_log writer (sync; very small payloads)
      consent/               # consent_records writer + check
      account/               # account creation, deletion lifecycle
    models/                  # SQLAlchemy ORM models
    schemas/                 # Pydantic request/response models
    migrations/              # Alembic versioned migrations
    templates/email/         # Jinja2 — verification, reset, deletion, export-ready
    workers/                 # FastAPI BackgroundTasks for v1 (export, deletion cron)
  tests/
    unit/
    integration/
    fixtures/
  Dockerfile
  alembic.ini
  pyproject.toml
```

**Background work in SP1 uses FastAPI BackgroundTasks** — no Celery, no Redis. The only async jobs in SP1 are (a) building a user's data-export ZIP and (b) the nightly account-deletion cron. Both are well-bounded. Celery + Redis enter when SP5 (LinkedIn ingest) needs durable, retryable, multi-step pipelines.

**Inter-service rule:** the frontend talks to FastAPI for all app data; the frontend talks directly to Supabase only for auth flows and (optionally) for cheap public reads behind RLS. **All mutations** to account-scoped data go through FastAPI so usage caps, audit log, and consent gates are enforced in exactly one place.

**API versioning:** every route under `/v1/...`. Breaking changes bump to `/v2/...`. Webhook routes live under `/webhooks/...` (un-versioned by convention).

**Health:**
- `/healthz` — process up, returns 200 always (used by Fly liveness)
- `/readyz` — process up + Postgres reachable + Supabase JWKS reachable; 503 if either fails

### 4.4 Database — Supabase Postgres (ap-southeast-2)

Two schemas: `auth` (Supabase-owned, untouched) and `public` (everything we own). Migrations live in `apps/api/src/migrations/` and ship with the API; the Supabase dashboard is read-only — production schema changes only flow through Alembic + the manual `db-migrate.yml` workflow.

See **Section 5** for the table-by-table definition.

**Row-Level Security:** every account-scoped table has a policy:
```sql
USING (account_id IN (
  SELECT account_id FROM public.account_users WHERE user_id = auth.uid()
))
```
FastAPI connects with the service-role key and bypasses RLS (mutations gated by application-level checks). Frontend reads use the anon key and rely on RLS. Belt + braces.

### 4.5 LLM provider abstraction

**Library:** LiteLLM. Unifies Anthropic, OpenAI, Google, Mistral, Bedrock, etc. behind an OpenAI-compatible interface. Handles streaming, tool calls, retries, callbacks.

**Wrapper API (`src/services/llm/client.py`):**
```python
class LLMClient:
    async def complete(
        self,
        messages: list[Message],
        *,
        account_id: UUID,
        user_id: UUID,
        workflow_slug: str,
        tools: list[Tool] | None = None,
        byo_key: BYOKey | None = None,
        stream: bool = False,
    ) -> CompletionResult: ...
```

**Per-call lifecycle:**
1. Resolve target model from `(account.plan_id, workflow_slug)` via a `config/model_routing.yaml` lookup. (Example: `free × review → claude-haiku-4-5`; `pro × tailor → claude-sonnet-4-6`.)
2. Estimate token budget (input tokens × 1.3 buffer). If `usage_meters.tokens_used + estimated > plan.token_quota_monthly`, raise `QuotaExceeded` (HTTP 429 with `Retry-After` header keyed to `current_period_end`).
3. If `byo_key` present, decrypt via vault, override LiteLLM credentials per-request.
4. Invoke LiteLLM `acompletion(...)`.
5. Post-call callback writes a `usage_events` row (kind=`tokens`, amount=actual tokens, metadata with model + cost estimate + workflow slug) and increments `usage_meters.tokens_used` in the same transaction.
6. Write an `audit_log` row if `workflow_slug` is sensitive (deferred — defaults to no-op until SP4 adds disclosure).

**SP1 status:** the wrapper, model routing config, quota check, metering writes, and unit tests all ship. No production code path calls `LLMClient.complete(...)` yet — SP2 plugs in.

**Encrypted BYO key vault:**
- Master key from env (`LLM_KEY_VAULT_MASTER`, 32-byte base64), Fly secret.
- Per-row encryption key derived via `HKDF(master, salt=user_id_bytes, info=b"llm-key-v1")`.
- Ciphertext stored in `llm_keys.ciphertext` (bytea). Last 4 chars in `llm_keys.last_4` for UI display.
- Rotation strategy: documented in `infra/runbooks/llm-key-rotation.md`. Re-encrypt-on-read pattern on master key rotation. Not implemented in SP1.
- No frontend surface in SP1. Schema + helpers + tests only.

### 4.6 File storage — Supabase Storage (Sydney)

Buckets, all private (signed-URL only):

| Bucket | Contents | RLS |
|---|---|---|
| `resumes` | user-uploaded resume files (.docx, .pdf, .txt) | account-scoped |
| `cover-letters` | user-uploaded cover letters | account-scoped |
| `jds` | JD source files (when user uploads vs. pastes URL) | account-scoped |
| `linkedin-imports` | LinkedIn ZIP exports (SP5 will populate) | account-scoped |
| `attachments` | misc — references, supporting docs | account-scoped |
| `exports` | user data-export ZIPs (TTL 7 days, signed-URL only) | account-scoped, expires_at column |

Per-account folder convention: `<bucket>/<account_id>/<file_uuid>.<ext>`.

**File metadata** lives in `public.files` (see Section 5). Storage SDK is the source of bytes; Postgres is the source of metadata. On upload, FastAPI issues a signed upload URL (frontend uploads direct to Storage), then frontend POSTs `/v1/files` to register metadata + verify the file exists in Storage.

### 4.7 Auth & consent

**Supabase Auth providers enabled in SP1:** email/password, magic link, Google OAuth. Email verification mandatory before any /app route works.

**Required-before-use sequence:**

1. **Sign up** → Supabase sends verification email (Resend handles delivery; template in `apps/api/templates/email/verification.html.j2`).
2. **Email verified** → user lands at `/accept-consent`. Page presents:
   - **Terms of Service** (required) — links to `/legal/terms`
   - **Privacy Policy** (required) — links to `/legal/privacy`, calls out AU Privacy Act + future GDPR expansion
   - **Sensitive-data consent** (required) — explicit AU language:
     > "I consent to Gold Leaf Resume processing sensitive information (including any neurodivergence-related details I choose to share) for the purpose of providing the service. I understand I can revoke this consent at any time, which will disable features that rely on this data."
   - **Marketing email** (optional, default off)
3. **Submit** → frontend calls `POST /v1/me/consent` with the four toggle values; backend writes four `consent_records` rows; consent gate clears.
4. **Forever after**: middleware `consent_gate` checks for non-revoked mandatory consent rows on every `/app/*` API call. Missing or revoked → 403 + frontend redirects to `/accept-consent`.

**Sessions:** Supabase access token (1h) + refresh token (rotated). `@supabase/ssr` handles refresh in the Next.js middleware. FastAPI verifies signature against the cached Supabase JWKS (refreshed every 60 minutes).

**Password reset / email change:** Supabase-hosted flows with branded templates.

**Account deletion lifecycle:**

1. User clicks "Delete my account" in Settings → confirmation modal with text-typed `DELETE` confirmation.
2. Backend sets `accounts.pending_deletion_at = now()`, sets `auth.users.banned_until = '2099-01-01'` (Supabase pattern that blocks login), writes `audit_log` event `account.deletion_requested`, emails "deletion scheduled for `now+30d`".
3. Daily Fly cron (`workers/deletion_sweeper.py`) finds accounts where `pending_deletion_at < now() - interval '30 days'`, hard-deletes the row + cascades, writes a record to `deleted_account_log` (account_id, deletion_reason, deleted_at — no PII), emails final confirmation.
4. During the 30-day window, the user can cancel via a signed-URL link in the scheduling email; cancel restores `auth.users.banned_until = null` and clears `pending_deletion_at`.

**Consent revocation:**
- User toggles off in Settings → `consent_records` row inserted with `revoked_at = now()`.
- If sensitive-data consent revoked: `subscriptions.features.sensitive_data_enabled = false`. Sensitive-flagged rows remain stored but are marked inaccessible-to-LLM-workflows. Future feature (SP7 refinement): user can request hard purge.
- If T&Cs or Privacy Policy revoked: account effectively unusable; `/app/*` routes 403; user must re-accept or proceed to deletion.

## 5. Data model (Postgres `public` schema)

All tables include `created_at timestamptz default now()`. Most include `updated_at timestamptz` with a trigger. UUIDs throughout for PKs. `account_id` is the tenancy boundary.

### 5.1 Identity & tenancy

**`accounts`**
| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | |
| `plan_id` | text FK→plans.id | default `'free'` |
| `region` | text | default `'au'` |
| `data_residency_locked` | bool | default `true` |
| `pending_deletion_at` | timestamptz | null unless scheduled |
| `deleted_at` | timestamptz | hard-delete sentinel, normally null (row removed) |
| `stripe_customer_id` | text | null in v1; populated at billing rollout |
| `created_at` | timestamptz | |

**`account_users`** (1:1 in SP1; ready for N:1 in SP5 Coach tier)
| Column | Type | Notes |
|---|---|---|
| `account_id` | uuid FK→accounts | |
| `user_id` | uuid FK→auth.users | |
| `role` | text | `'owner'` in v1; future: `'coach'`, `'client'`, `'viewer'` |
| PK | (account_id, user_id) | |

**`profiles`**
| Column | Type | Notes |
|---|---|---|
| `user_id` | uuid PK FK→auth.users | |
| `display_name` | text | nullable |
| `focus_areas` | text[] | carried over from v1 skill |
| `healthy_weekly_rate` | int | carried over; user-defined |
| `pacing_notes` | text | carried over |
| `log_handoffs` | bool | carried over; default true |
| `disclosure_preferences` | jsonb | carried over from v1; structure TBD by SP4 |
| `accessibility_prefs` | jsonb | `{reduced_motion, font_scale, high_contrast, ...}` |

### 5.2 Billing-ready

**`plans`** (seeded, not user-mutable)
| Column | Type | Notes |
|---|---|---|
| `id` | text PK | slug — `'free'`, future `'pro'`, `'coach'` |
| `display_name` | text | |
| `price_aud_monthly` | int | cents; 0 for free |
| `price_aud_yearly` | int | cents; 0 for free |
| `token_quota_monthly` | int | 50_000 for free |
| `workflow_quota_monthly` | int | 20 for free |
| `storage_quota_mb` | int | 100 for free |
| `features` | jsonb | feature-flag map |
| `stripe_price_id_monthly` | text | null in v1 |
| `stripe_price_id_yearly` | text | null in v1 |

SP1 seed: a single `free` row.

**`subscriptions`**
| Column | Type | Notes |
|---|---|---|
| `account_id` | uuid PK FK→accounts | |
| `plan_id` | text FK→plans.id | |
| `status` | text | `'active'`, `'trialing'`, `'past_due'`, `'canceled'` |
| `current_period_start` | timestamptz | |
| `current_period_end` | timestamptz | rolling monthly for free |
| `cancel_at_period_end` | bool | default false |
| `stripe_subscription_id` | text | null in v1 |

**`usage_meters`**
| Column | Type | Notes |
|---|---|---|
| `account_id` | uuid PK FK→accounts | |
| `period_start` | timestamptz | matches subscriptions.current_period_start |
| `tokens_used` | bigint | default 0 |
| `workflows_run` | int | default 0 |
| `storage_bytes` | bigint | default 0 |

Reset on period rollover by the same cron that handles deletion sweeps.

**`usage_events`** (immutable, append-only)
| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | |
| `account_id` | uuid FK | |
| `user_id` | uuid FK | |
| `kind` | text | `'tokens'`, `'workflow'`, `'file_upload'`, `'file_delete'` |
| `amount` | bigint | tokens, bytes, or 1 (per workflow) |
| `metadata` | jsonb | `{model, workflow_slug, cost_aud_cents, ...}` |
| `created_at` | timestamptz | |

**`billing_events`** (immutable, append-only — empty in v1)
| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | |
| `account_id` | uuid FK (nullable for system events) | |
| `event_type` | text | `'stripe.invoice.paid'`, etc. |
| `stripe_event_id` | text unique | idempotency |
| `payload` | jsonb | verbatim Stripe payload |
| `processed_at` | timestamptz | |

### 5.3 Consent & audit

**`consent_records`** (immutable, append-only)
| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | |
| `user_id` | uuid FK→auth.users | |
| `kind` | text | `'tos'`, `'privacy_policy'`, `'sensitive_data_au'`, `'marketing_email'`, `'byo_llm_key_storage'` |
| `version` | text | semver of the legal doc, e.g. `'2026-05-18'` |
| `granted_at` | timestamptz | |
| `revoked_at` | timestamptz | null unless revoked |
| `ip_address` | inet | |
| `user_agent` | text | |

**`audit_log`** (immutable, append-only)
| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | |
| `account_id` | uuid FK | |
| `actor_user_id` | uuid FK→auth.users (nullable for system events) | |
| `event` | text | dot-namespaced — `account.created`, `consent.granted`, `data.exported`, `sensitive_data.accessed`, etc. |
| `metadata` | jsonb | |
| `ip_address` | inet | |
| `user_agent` | text | |
| `created_at` | timestamptz | |

**`deleted_account_log`** (retained 7 years per APP retention rule; no PII)
| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | |
| `account_id` | uuid | not FK (parent gone) |
| `deletion_reason` | text | `'user_requested'`, `'admin'`, `'tos_violation'` |
| `deleted_at` | timestamptz | |

### 5.4 Object & support tables

All carry `account_id uuid FK NOT NULL` (except `llm_keys`, which is `user_id`-scoped), are RLS-policy-enabled, and most carry a `sensitive_data bool default false`. `files` and `llm_keys` are functional in SP1; the rest are defined here so SP2–SP5 can populate them without schema migration.

| Table | Key columns | Populated by |
|---|---|---|
| `files` | `id`, `account_id`, `bucket`, `storage_path`, `kind`, `mime_type`, `size_bytes`, `sha256`, `sensitive_data` | SP1 (uploads work; no UI for it until SP2) |
| `resumes` | `id`, `account_id`, `title`, `current_version_id`, `source` | SP2 |
| `resume_versions` | `id`, `resume_id`, `version_num`, `content_jsonb`, `source_file_id`, `parsed_text`, `generated_by`, `parent_version_id` | SP2 |
| `cover_letters` | `id`, `account_id`, `jd_id`, `resume_version_id`, `content_jsonb`, `generated_by` | SP3 |
| `jds` | `id`, `account_id`, `source_url`, `parsed_jsonb`, `analyzer_findings_jsonb`, `sensitive_data` | SP3 |
| `applications` | `id`, `account_id`, `jd_id`, `resume_version_id`, `cover_letter_id`, `status`, `channel`, `submitted_at`, `agency` | SP4 |
| `outcomes` | `id`, `application_id`, `kind`, `occurred_at`, `notes` | SP4 |
| `linkedin_imports` | `id`, `account_id`, `import_metadata_jsonb`, `sensitive_data`, `ingested_at` | SP5 |
| `llm_keys` | `id`, `user_id`, `provider`, `ciphertext` (bytea), `last_4`, `created_at`, `last_used_at` | SP1 (schema + helpers only) |

### 5.5 Migrations

Alembic, autogenerated from SQLAlchemy models, hand-edited where needed. SP1 ships migration `0001_initial_schema` which creates every table above. Future sub-projects add columns / new tables via numbered migrations. Migration files committed to git; never edited after merge.

Migration safety: every PR-stage CI run applies migrations against an ephemeral Postgres container and runs a smoke query. Production migrations run via manual `db-migrate.yml` GitHub Actions workflow (never automatic on deploy).

## 6. Demoable end state (acceptance criteria)

SP1 is complete when a fresh tester can do all of the following without intervention:

1. Open `goldleafresume.<tld>` and see a minimal landing page with sign-up + sign-in CTAs.
2. Sign up with email/password OR magic link OR Google OAuth.
3. Receive a verification email branded "Gold Leaf Resume", click through, land at `/accept-consent`.
4. See and toggle the four consent items, submit.
5. Land at `/app/dashboard` and see the sidebar nav with empty placeholder pages for each tab.
6. Open `/app/settings`, edit display name + focus areas + healthy weekly rate + pacing notes, save, and see the change persist across reload.
7. Open `/app/settings/data-rights`, click "Export my data", receive an email with a signed-URL link, download a ZIP containing JSON files of all account data (mostly empty in SP1, but the export pipeline runs).
8. Open `/app/settings/audit`, see a list of audit events covering signup, consent grants, profile changes, export request.
9. Open `/app/settings/account`, click "Delete my account", confirm with typed `DELETE`, receive "deletion scheduled" email.
10. Within 30 days, log in (blocked by Supabase banned_until), click the cancel-deletion link in the email → restored to working state.
11. Or, wait 30 days (or admin-run the cron locally), confirm the account row is gone, the data is gone, and the `deleted_account_log` row exists.

Plus, behind the scenes (verified via logs + DB inspection):
- Every action above writes the appropriate `audit_log` and/or `consent_records` row.
- `usage_meters` row exists for the account with zeros.
- `subscriptions` row exists pointing at `plan_id='free'`.
- Sentry receives a test error from both web and api.
- `/healthz` and `/readyz` return as expected.
- The `LLMClient.complete(...)` wrapper passes its unit tests (without making any real LLM call).
- The vault encrypt/decrypt round-trips correctly in unit tests.
- The Stripe webhook receiver returns 501 with a structured log line.

## 7. Stripe-readiness without Stripe

The point: no Stripe code path runs in v1, but **the data model, the middleware, and the scaffolding are in place so a future sub-project can wire billing in without a schema change**.

| Concern | SP1 state |
|---|---|
| Plan catalogue | `plans` table, seeded with `free` |
| Per-account plan binding | `subscriptions` table, every account gets a `free` row at signup |
| Usage caps | `@require_plan(features=[...])` decorator exists, returns no-op against `free` |
| Token quota enforcement | Pre-call check in `LLMClient` already enforces `plans.token_quota_monthly` |
| Workflow quota enforcement | `@enforce_workflow_quota` decorator exists; will be applied at SP2 |
| Storage quota enforcement | File-upload service checks `usage_meters.storage_bytes + size_bytes` against `plans.storage_quota_mb` |
| Webhook receiver | `/webhooks/stripe` exists, signature-verification helper present, returns 501 |
| Idempotency | `billing_events.stripe_event_id` is unique-indexed |
| Customer ID storage | `subscriptions.stripe_subscription_id` + `accounts.stripe_customer_id` columns exist, nullable |
| Currency | AUD assumed throughout; multi-currency post-v1 |
| Tax | Not modelled; Stripe Tax will handle at billing rollout |

## 8. Observability

- **Sentry** — frontend (`@sentry/nextjs`) + backend (`sentry-sdk[fastapi]`). PII scrubber drops `email`, `phone`, anything matching a configurable list of ND-disclosure patterns, anything from a row marked `sensitive_data = true` (server-side). Source maps uploaded on Vercel build.
- **Structured logs** — `structlog` JSON to stdout. Fields: `timestamp`, `level`, `request_id`, `account_id` (when known), `user_id` (when known), `route`, `latency_ms`, `status`, `event`. Fly's log stream captures; viewable via `fly logs` for SP1. Logflare or Better Stack shipping in SP7.
- **Health/readiness** — described in §4.3.
- **No Prometheus/Datadog/OpenTelemetry in SP1.** Custom metrics enter when there's something worth measuring — likely SP3 (response latency on Tailor) or SP6 (assistant tool-call success rates).

## 9. CI/CD & infrastructure

### 9.1 Repo layout (monorepo)

```
gold-leaf-resume/
  apps/
    web/                        # Next.js
    api/                        # FastAPI
  packages/
    shared-types/               # auto-generated TS types from OpenAPI
    design-tokens/              # Tailwind config + CSS variables
  infra/
    fly/
      Dockerfile.api
      fly.toml
    supabase/
      seed.sql                  # plans, sample legal versions
      types.ts                  # Supabase-generated DB types
    runbooks/
      llm-key-rotation.md
      production-incident.md
      data-export-debug.md
  docs/
    specs/                      # this file + SP2+ specs as they land
    plans/                      # implementation plans (writing-plans output)
  .github/workflows/
    test.yml
    deploy-api.yml
    deploy-web.yml
    db-migrate.yml
  pnpm-workspace.yaml
  pyproject.toml                # workspace-style for uv
  README.md
```

### 9.2 Tooling

- **JS:** pnpm workspaces, biome (lint + format), tsc (typecheck), vitest (test), playwright (e2e — SP7).
- **Python:** uv for env mgmt + lock, ruff (lint + format), mypy (typecheck), pytest (test).
- **OpenAPI → TS:** `openapi-typescript-codegen` runs in CI; output committed to `packages/shared-types` for deterministic builds.

### 9.3 GitHub Actions

- `test.yml` — every PR. Matrix: lint, typecheck, unit tests, Alembic migration check against ephemeral Postgres.
- `deploy-api.yml` — on `main` push touching `apps/api/**`: build Docker, `flyctl deploy --remote-only`.
- `deploy-web.yml` — Vercel handles natively on `main` push touching `apps/web/**` or shared.
- `db-migrate.yml` — `workflow_dispatch` only; never automatic. Runs `alembic upgrade head` against the chosen environment with explicit operator confirmation.

### 9.4 Environments

| Env | Web | API | Supabase | Stripe | Notes |
|---|---|---|---|---|---|
| `local` | `next dev` on `:3000` | `uvicorn` on `:8000` | Supabase CLI local stack | mock | Docker Compose orchestrates |
| `staging` | Vercel preview → `staging.goldleafresume.<tld>` | Fly app `gold-leaf-staging` on `:443` | Supabase free-tier project | test mode (when introduced) | Region `syd` |
| `production` | Vercel prod → `goldleafresume.<tld>` | Fly app `gold-leaf-prod` | Supabase pro project | live (post-v1) | Region `syd` |

Domain choice (`.com`, `.com.au`, `.app`, `.io`) finalised before staging deploy. Default working assumption: `.com.au` (AU-first positioning) with `.com` redirect if available.

### 9.5 Secrets

- Fly secrets for API: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `LLM_KEY_VAULT_MASTER`, `RESEND_API_KEY`, `SENTRY_DSN_API`, `ANTHROPIC_API_KEY` (for default platform-paid path), `STRIPE_*` (post-v1).
- Vercel env vars for web: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SENTRY_DSN_WEB`.
- `.env.example` files in `apps/web/` and `apps/api/` checked in; nothing real.

## 10. Security & privacy posture

- **Data residency:** Postgres + Storage + Auth all `ap-southeast-2`. Resend transactional email transits via Resend's infrastructure; we never put resume/JD/disclosure content in email bodies — only links to signed-URL downloads and minimal status text.
- **Encryption at rest:** Supabase managed (AES-256). BYO LLM keys: additional application-layer Fernet encryption (Section 4.5).
- **Encryption in transit:** TLS everywhere. HSTS on web + api. mTLS not required for SP1.
- **Authentication:** Supabase JWT verified server-side every request. JWKS cached 60 min.
- **Authorisation:** RLS on every account-scoped table; service-role client bypasses RLS and enforces at app layer.
- **Sensitive data marker:** `sensitive_data bool` on rows that may contain ND disclosure or other special-category info. Reading such rows from an LLM workflow writes an `audit_log` entry. (SP4 wires the actual disclosure flow.)
- **Consent gating:** middleware blocks `/app/*` API calls if mandatory consent is missing/revoked.
- **Audit log:** every privacy-relevant event written to `audit_log` and visible to the user.
- **Data export:** `/v1/me/export` produces a ZIP of all account data + raw files. APP/GDPR-compatible.
- **Data deletion:** 30-day pending window + hard delete. `deleted_account_log` retains an event record (no PII) for 7 years.
- **PII scrubbing in Sentry:** drop `email`, `phone`, common ND-disclosure patterns, anything from `sensitive_data=true` rows.
- **No SOC2 / ISO 27001 in v1.** Posture documented in `infra/runbooks/security-posture.md`. Revisit at first enterprise-tier conversation (post-v1).

## 11. Open questions / risks

- **Domain TLD** (`.com.au` / `.com` / `.app` / `.io`): finalise before staging deploy. Default working assumption: `.com.au` with `.com` redirect if available.
- **Email-from address branding:** `hello@` vs. `noreply@` vs. `team@`. Default: `hello@goldleafresume.<tld>` with reply-to set to `support@`.
- **Free-plan quotas (50k tokens, 20 workflows, 100 MB):** numbers are placeholders. Tune after SP2 ships and we observe real per-session token usage on Review/Tailor.
- **LiteLLM vs. provider SDKs:** if LiteLLM friction shows up early (e.g., tool-calling parity issues across Anthropic vs OpenAI), fall back to direct Anthropic SDK for SP1's wrapper interface, keeping the abstraction shape but with a simpler implementation. Decide in implementation, not now.
- **Magic-link UX on mobile:** verify Google OAuth + magic link flows on iOS Safari + Android Chrome before SP1 ships. Likely fine — both are Supabase defaults — but worth manual verification.
- **Vercel function region pinning:** if SSR latency from US to AU users is unpleasant, switch the Next.js app to Cloudflare Workers (which has Sydney) or to a Fly-hosted Next.js. Defer decision until SP7's accessibility/performance audit.
- **Plan-quota period semantics:** v1 uses calendar-month rollover for `free`. Stripe billing periods are subscription-anchored (e.g., signup-date anchored). When billing lands, document the migration of period semantics and back-fill `usage_meters.period_start` consistently.

## 12. References

- Predecessor product: BRAINS Resume Skill v1.4.1 (local Streamlit + Claude Code) — `https://github.com/shard-BRAINS/BRAINS-resume-skill`
- BRAINS Brand standards v1.0 (May 2026) — applies to BRAINS Incubator footer attribution and any cross-product references
- Australian Privacy Principles (APP 3, 6, 11, 12) — sensitive information handling, access/correction, security, data export
- GDPR (deferred to UK/EU expansion; data model already compatible)
- Existing Python validators: `scripts/validators/{bias_scan,ats_check,ai_signal_check,integrity_check,jd_analyzer}.py` — SP2+ ports these to FastAPI services
- Existing data layer: `scripts/tracker/*` — SP1 schema design carries over the concepts (resume_versions, cover_letters, jds, applications, outcomes) to multi-tenant Postgres

## 13. Out-of-scope deferrals (consolidated)

For one-glance clarity, everything explicitly deferred from SP1:

- **SP2:** Resume review, edit, create, de-AI scan, final check workflows
- **SP3:** JD analyzer, tailor, cover letter generation
- **SP4:** Application tracker, pre-application check, disclosure decision flow
- **SP5:** LinkedIn ZIP ingest, profile rewrite, resume↔LinkedIn consolidation, career-change translation. Coach tier (multi-user accounts) UI surface.
- **SP6:** Always-on AI assistant sidebar with tool-calling across workflows
- **SP7:** Marketing landing page polish, public help docs, accessibility audit, Stripe rollout, Apple Sign-In + passkeys + SAML/SSO, BYO LLM key UI surface, hard-purge-on-consent-revoke, multi-region (UK + US), session replay, OpenTelemetry, mobile native apps, cooperative editing / public profile sharing
- **Excluded from cloud product entirely:** public REST API for third-party developers

---

**End of SP1 spec.**
