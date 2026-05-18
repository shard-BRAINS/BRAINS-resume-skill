# Gold Leaf Resume — SP1·M2: Backend Auth + Consent Middleware Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the API authentication and consent layer so any subsequent endpoint can rely on `current_user`, `current_account`, and consent-gated execution. The FastAPI app verifies Supabase-issued JWTs, lazy-creates an `accounts` row on first authed request, and blocks `/v1/*` traffic (except auth/consent/health) when mandatory consent rows are missing or revoked. Two new endpoints: `GET /v1/me` (returns the authed user + their account + consent status) and `POST /v1/me/consent` (records one consent decision per call). `audit_log` rows written for every signup, consent grant, and consent revoke. Out of scope: any frontend (M3), refresh-token rotation logic on the backend (Supabase handles it).

**Architecture:** FastAPI middleware layered in this order — request_id → JWT verify → account resolve (lazy-create) → consent gate → route handler. Each layer attaches data to `request.state` for downstream consumers. JWT verification uses `pyjwt` against the Supabase JWT secret (HS256) — the canonical Supabase auth pattern. JWKS-based verification is a future enhancement, not in M2. New `services/` modules: `auth.py` (JWT decode + claim extraction), `accounts.py` (lazy-create), `consent.py` (record + check). All DB writes go through a single async session per request.

**Tech Stack additions on top of M1:** `pyjwt[crypto]` (HS256 + future RS256), `python-multipart` (FastAPI body parsing, transitively needed). No new JS deps.

**Predecessor:** SP1·M1 (DB schema + Supabase local stack) — tag `sp1-m1` on `gold-leaf-resume`.
**Spec:** [docs/specs/2026-05-18-sp1-gold-leaf-resume-platform-foundation.md](../specs/2026-05-18-sp1-gold-leaf-resume-platform-foundation.md) §4.3 (backend layout), §4.7 (auth + consent flow), §5.1 (Account / AccountUser / Profile tables), §5.3 (ConsentRecord / AuditLog tables).

**Demoable end state:**
1. Local: a developer signs up via Supabase Studio (or the CLI), copies the resulting JWT, and hits `curl -H "Authorization: Bearer <jwt>" http://localhost:8000/v1/me`. First call lazy-creates an `accounts` row + an `account_users` join + a `subscriptions` row (free) + a `usage_meters` row + an `audit_log` row (`account.created`). Response: a JSON document with `user_id`, `account_id`, `email`, `plan_id: "free"`, `consent_status: {tos: false, privacy_policy: false, sensitive_data_au: false, marketing_email: false}`.
2. Same user hits `POST /v1/me/consent` with `{"kind": "tos", "version": "2026-05-18", "granted": true}` — backend writes a `consent_records` row + an `audit_log` row (`consent.granted`).
3. Calling any other `/v1/me/*` route without the three mandatory consents (tos, privacy_policy, sensitive_data_au) returns HTTP 403 with body `{"error": "consent_required", "missing": [...]}`.
4. After granting all three, the user can hit any `/v1/me/*` route successfully.
5. `audit_log` for the account shows the create event + every consent grant.
6. `GET /v1/me/consent/log` returns the user's full consent history (granted + revoked, immutable append-only).
7. CI: a new `auth-flow` integration test job spins up ephemeral Postgres, generates test JWTs with a known secret, exercises `/v1/me`, consent grant/revoke, and 403 on missing consent — all green.
8. Tag `sp1-m2` exists on `main`, reached via squash-merge from feature branch `m2-backend-auth-consent`.

---

## Open prerequisites (resolve before Task 1)

- [ ] **Locate the Supabase v2 local JWT secret.** The CLI v2 does not surface this in `supabase status`. Three discovery paths:
   1. Inspect `c:/gold-leaf-resume/infra/supabase/.temp/cli/.env` or `.../config.json` — the CLI stores generated secrets here.
   2. Run `supabase secrets list` from `infra/supabase/`.
   3. Query the running stack: `docker exec supabase_kong_gold-leaf-resume env | grep -i JWT` (Kong reads the JWT secret as an env var).
   4. Fallback: the local default for Supabase CLI v2 is the well-known string `super-secret-jwt-token-with-at-least-32-characters-long`. If methods 1-3 confirm this value, we're done.

  Whichever value is found, paste it into `apps/api/.env` as `SUPABASE_JWT_SECRET=<value>`. CI uses its own test secret.

- [ ] **Test user creation strategy.** For local manual testing, create a user via Supabase Studio (http://127.0.0.1:54323 → Authentication → Users → Add user). Copy the access token from the user's session (the Studio UI exposes it). Use that JWT in `curl` calls during dev verification.

- [ ] **Feature branch workflow.** All M2 work lives on branch `m2-backend-auth-consent`. PR squash-merge into `main` at the end.

- [ ] **M1 model `server_default` cleanup**. The M1 followup is the first task here so the next autogeneration (if any happens in M2) doesn't re-introduce the JSONB / interval bug. T1 handles this.

---

## File Structure

```
gold-leaf-resume/                                     (existing from M1)
├── apps/api/
│   ├── pyproject.toml                                +pyjwt[crypto], python-multipart
│   ├── src/
│   │   ├── config.py                                 MODIFIED — JWT secret now required (no placeholder default)
│   │   ├── deps.py                                   NEW — FastAPI deps for current_user, current_account, db session
│   │   ├── main.py                                   MODIFIED — register middleware stack + new routes
│   │   ├── exceptions.py                             NEW — typed app exceptions + handlers
│   │   ├── middleware/
│   │   │   ├── __init__.py                           NEW
│   │   │   ├── request_id.py                         NEW — correlation IDs into request.state + structlog
│   │   │   ├── auth.py                               NEW — verify JWT, attach user_id + email to request.state
│   │   │   └── consent_gate.py                       NEW — block /v1/* when mandatory consents missing
│   │   ├── services/
│   │   │   ├── __init__.py                           NEW
│   │   │   ├── auth.py                               NEW — decode_jwt(token) → AuthedUser
│   │   │   ├── accounts.py                           NEW — ensure_account(user_id, email) → Account (lazy create)
│   │   │   ├── consent.py                            NEW — record_consent(...) + missing_mandatory_consents(...)
│   │   │   └── audit.py                              NEW — write_audit_log(account_id, actor_user_id, event, metadata)
│   │   ├── routes/
│   │   │   ├── __init__.py                           NEW
│   │   │   └── v1/
│   │   │       ├── __init__.py                       NEW
│   │   │       ├── me.py                             NEW — GET /v1/me
│   │   │       └── consent.py                        NEW — POST /v1/me/consent, GET /v1/me/consent/log
│   │   ├── schemas/
│   │   │   ├── __init__.py                           NEW
│   │   │   ├── me.py                                 NEW — Pydantic response schemas for /v1/me
│   │   │   └── consent.py                            NEW — Pydantic request/response schemas for consent
│   │   └── models/                                   MODIFIED — server_default cleanup (T1)
│   │       ├── billing.py                            sa.text() for JSONB + interval defaults
│   │       ├── consent.py                            sa.text() for JSONB default
│   │       └── objects.py                            sa.text() for JSONB defaults
│   ├── migrations/versions/
│   │   └── 0003_model_default_cleanup.py             NEW (only if autogenerate produces a diff — usually a no-op)
│   ├── tests/
│   │   ├── conftest.py                               MODIFIED — add jwt_factory fixture + auth helpers
│   │   ├── test_auth_middleware.py                   NEW — JWT verify unit + 401 cases
│   │   ├── test_me_endpoint.py                       NEW — /v1/me lazy-create + response shape
│   │   ├── test_consent_flow.py                      NEW — record/revoke/list consent + 403 on missing
│   │   └── test_audit_writes.py                      NEW — confirm audit_log rows on auth + consent events
│   └── seed/
│       └── plans.py                                  (unchanged from M1)
│
├── .github/workflows/test.yml                        MODIFIED — add auth-flow job (or expand migration-check)
│
└── docs/                                             (existing from M0/M1)
```

**Why a separate `routes/v1/` package**: every API endpoint we ever ship will live under `/v1/...`. Putting them in their own package matches the spec §4.3 layout and makes it trivial for SP2+ to add new route modules without crowding `main.py`.

**Why `deps.py`**: FastAPI's `Depends(...)` works best when dependencies live in a stable, shallow module. `deps.py` exports `current_user`, `current_account`, `get_db` so route modules can `from src.deps import current_user`.

**Why `services/auth.py` and `middleware/auth.py` (separate files):** the middleware wraps every request, the service is the pure function that decodes a token. The middleware calls the service. Splitting makes the service unit-testable without a FastAPI request.

---

## Task 1: Branch + M1 model `server_default` cleanup

**Files:**
- Modify: `apps/api/src/models/billing.py`
- Modify: `apps/api/src/models/consent.py`
- Modify: `apps/api/src/models/objects.py`

This was queued as a followup from M1·T10 — the autogenerated 0001 migration had to be hand-fixed for JSONB and interval `server_default` values because Alembic mis-quotes Python string defaults. Fixing the models to use `sa.text(...)` directly prevents the bug from recurring on future autogenerations.

- [ ] **Step 1: Create the feature branch**

```bash
cd c:/gold-leaf-resume && git checkout main && git pull && git checkout -b m2-backend-auth-consent
```

- [ ] **Step 2: Patch `apps/api/src/models/billing.py`**

Use Read + Edit. The model `Plan.features` currently has:
```python
features: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="'{}'::jsonb")
```
Change to:
```python
features: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=sa.text("'{}'::jsonb"))
```

Also `UsageEvent.extra`:
```python
extra: Mapped[dict] = mapped_column(
    "metadata",
    JSONB,
    nullable=False,
    server_default="'{}'::jsonb",
)
```
becomes:
```python
extra: Mapped[dict] = mapped_column(
    "metadata",
    JSONB,
    nullable=False,
    server_default=sa.text("'{}'::jsonb"),
)
```

And `Subscription.current_period_end`:
```python
current_period_end: Mapped[datetime] = mapped_column(
    nullable=False,
    server_default="now() + interval '30 days'",
)
```
becomes:
```python
current_period_end: Mapped[datetime] = mapped_column(
    nullable=False,
    server_default=sa.text("now() + interval '30 days'"),
)
```

Add `import sqlalchemy as sa` at the top if not present.

- [ ] **Step 3: Patch `apps/api/src/models/consent.py`**

`AuditLog.extra`:
```python
extra: Mapped[dict] = mapped_column(
    "metadata", JSONB, nullable=False, server_default="'{}'::jsonb"
)
```
becomes:
```python
extra: Mapped[dict] = mapped_column(
    "metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
)
```

Add `import sqlalchemy as sa` if not present.

- [ ] **Step 4: Patch `apps/api/src/models/objects.py`**

`JD.parsed_jsonb` and `JD.analyzer_findings_jsonb`:
```python
parsed_jsonb: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="'{}'::jsonb")
analyzer_findings_jsonb: Mapped[dict] = mapped_column(
    JSONB, nullable=False, server_default="'{}'::jsonb"
)
```
become:
```python
parsed_jsonb: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=sa.text("'{}'::jsonb"))
analyzer_findings_jsonb: Mapped[dict] = mapped_column(
    JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
)
```

Add `import sqlalchemy as sa` if not present.

- [ ] **Step 5: Verify the model package still imports cleanly**

```bash
cd c:/gold-leaf-resume/apps/api && uv run python -c "from src.models import Base; print(len(Base.metadata.tables), 'tables')"
```
Expected: `20 tables`.

- [ ] **Step 6: Check Alembic doesn't see drift**

Make sure Supabase local stack is running:
```bash
cd c:/gold-leaf-resume && pnpm db:status 2>&1 | head -3
# if not running:
# pnpm db:start
```

Then check for autogeneration diff:
```bash
cd c:/gold-leaf-resume/apps/api && uv run --env-file=.env alembic check 2>&1
```

Two acceptable outcomes:
- **No diff** (Alembic considers `sa.text("'{}'::jsonb")` equivalent to the literal `'{}'::jsonb` already in the DB column defaults). Migration not needed. Skip to Step 8.
- **Drift detected** — generate a no-op-effectively migration that just re-statements the defaults. In this case:
  ```bash
  cd c:/gold-leaf-resume/apps/api && uv run --env-file=.env alembic revision --autogenerate -m "normalize server defaults to sa.text" --rev-id 0003
  ```
  Review the generated `0003_normalize_server_defaults_to_sa_text.py` — it should be small (only ALTER COLUMN ... SET DEFAULT for the 5 changed columns). If it contains anything else, investigate.
  Apply it:
  ```bash
  cd c:/gold-leaf-resume/apps/api && uv run --env-file=.env alembic upgrade head
  ```

- [ ] **Step 7: Verify schema tests still pass**

```bash
cd c:/gold-leaf-resume/apps/api && uv run --env-file=.env pytest -v
```
Expected: 4 passed (test_health + 3 schema tests).

- [ ] **Step 8: Commit**

```bash
cd c:/gold-leaf-resume && git add apps/api/src/models/ apps/api/migrations/versions/ 2>/dev/null || true
git commit -m "refactor(api): use sa.text() for JSONB + interval server_defaults (avoids Alembic autogen quoting bug)"
```

If no migration was generated in Step 6, the commit only contains model changes — fine.

---

## Task 2: Add auth + multipart deps

**Files:**
- Modify: `apps/api/pyproject.toml`

- [ ] **Step 1: Add deps**

In `c:/gold-leaf-resume/apps/api/pyproject.toml`, append to the `dependencies` array:
```toml
  "pyjwt[crypto]==2.10.1",
  "python-multipart==0.0.20",
```

- [ ] **Step 2: Sync**

```bash
cd c:/gold-leaf-resume/apps/api && uv sync
```

- [ ] **Step 3: Verify imports**

```bash
cd c:/gold-leaf-resume/apps/api && uv run python -c "import jwt; print('pyjwt', jwt.__version__)"
```
Expected: `pyjwt 2.10.1`.

- [ ] **Step 4: Commit**

```bash
cd c:/gold-leaf-resume && git add apps/api/pyproject.toml apps/api/uv.lock
git commit -m "feat(api): add pyjwt + python-multipart deps for auth middleware"
```

---

## Task 3: Settings — JWT secret becomes required, audience claim added

**Files:**
- Modify: `apps/api/src/config.py`
- Modify: `apps/api/.env.example`
- Modify: `apps/api/.env` (local, gitignored — paste the real local secret)

- [ ] **Step 1: Update `config.py`**

Open `c:/gold-leaf-resume/apps/api/src/config.py`. Change the `supabase_jwt_secret` field to be required (no default), and add `supabase_jwt_audience` + `supabase_jwt_issuer`:

Replace:
```python
    supabase_jwt_secret: str = Field(
        default="deferred-to-m2",
        description=(
            "JWT signing secret used to verify Supabase-issued tokens. CLI v2 doesn't expose "
            "this in `supabase status`; SP1·M2 sources it from local Supabase config when auth wires in."
        ),
    )
```

With:
```python
    supabase_jwt_secret: str = Field(
        description=(
            "Supabase JWT signing secret (HS256). Local stack default is "
            "'super-secret-jwt-token-with-at-least-32-characters-long' for Supabase CLI v2. "
            "Production: get from project settings."
        ),
    )
    supabase_jwt_audience: str = Field(
        default="authenticated",
        description="Expected `aud` claim in user JWTs. Supabase issues 'authenticated' for logged-in users.",
    )
    supabase_jwt_issuer: str = Field(
        default="http://127.0.0.1:54321/auth/v1",
        description=(
            "Expected `iss` claim in user JWTs. Local: http://127.0.0.1:54321/auth/v1. "
            "Production: <supabase_url>/auth/v1."
        ),
    )
```

- [ ] **Step 2: Update `.env.example`**

In `c:/gold-leaf-resume/apps/api/.env.example`, replace:
```bash
# JWT secret is not exposed by `supabase status` in CLI v2. Placeholder is fine for M1;
# M2 (auth + consent) sources the real value from infra/supabase/.temp or via Supabase API.
SUPABASE_JWT_SECRET=deferred-to-m2
```

With:
```bash
# Supabase JWT signing secret. For the local CLI v2 stack this is the well-known default:
SUPABASE_JWT_SECRET=super-secret-jwt-token-with-at-least-32-characters-long
SUPABASE_JWT_AUDIENCE=authenticated
SUPABASE_JWT_ISSUER=http://127.0.0.1:54321/auth/v1
```

- [ ] **Step 3: Update local `.env`**

Edit `c:/gold-leaf-resume/apps/api/.env` (gitignored). Replace `SUPABASE_JWT_SECRET=deferred-to-m2` with `SUPABASE_JWT_SECRET=super-secret-jwt-token-with-at-least-32-characters-long`.

If the actual JWT secret discovered via the "Open prerequisites" methods is different, use that instead — verify via decoding a real Supabase-issued JWT in Step 5.

- [ ] **Step 4: Verify Settings still loads**

```bash
cd c:/gold-leaf-resume/apps/api && uv run --env-file=.env python -c "from src.config import get_settings; s = get_settings(); print(len(s.supabase_jwt_secret), 'chars in secret;', s.supabase_jwt_audience)"
```
Expected: `64 chars in secret; authenticated` (or whatever your secret length is).

- [ ] **Step 5: Verify the secret can decode a real Supabase-issued JWT**

In Supabase Studio (http://127.0.0.1:54323), create a test user (Authentication → Users → "Add user" → email/password). Then in the SQL Editor, query a JWT for that user (or sign in via the Studio playground).

Get a JWT and run:
```bash
cd c:/gold-leaf-resume/apps/api && uv run --env-file=.env python -c "
import jwt
from src.config import get_settings
s = get_settings()
token = '<paste JWT here>'
decoded = jwt.decode(token, s.supabase_jwt_secret, algorithms=['HS256'], audience=s.supabase_jwt_audience, issuer=s.supabase_jwt_issuer)
print(decoded)
"
```
Expected: a dict with `sub`, `email`, `aud`, `iss`, `exp`, etc. If verification fails with `InvalidSignatureError`, the secret is wrong — try the other discovery methods in "Open prerequisites".

If `InvalidIssuerError` — the iss claim doesn't match `http://127.0.0.1:54321/auth/v1`. Update `SUPABASE_JWT_ISSUER` in `.env` to match the actual claim, and update `.env.example` similarly.

- [ ] **Step 6: Commit**

```bash
cd c:/gold-leaf-resume && git add apps/api/src/config.py apps/api/.env.example
git commit -m "feat(api): require Supabase JWT secret + audience + issuer in Settings"
```

(Note: `apps/api/.env` is gitignored — not staged.)

---

## Task 4: JWT decode service

**Files:**
- Create: `apps/api/src/services/__init__.py`
- Create: `apps/api/src/services/auth.py`
- Create: `apps/api/src/exceptions.py`
- Create: `apps/api/tests/test_auth_service.py`

- [ ] **Step 1: Create the services package**

```bash
cd c:/gold-leaf-resume/apps/api && mkdir -p src/services && touch src/services/__init__.py
```

- [ ] **Step 2: Create `src/exceptions.py`**

```python
"""Typed application exceptions.

These get caught by FastAPI exception handlers in main.py and mapped to
appropriate HTTP responses.
"""
from __future__ import annotations


class AppError(Exception):
    """Base class for all app-level errors that should map to non-500 responses."""

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AuthError(AppError):
    """JWT verification failed or token is missing."""

    status_code = 401
    error_code = "unauthenticated"


class ConsentRequired(AppError):
    """User has not granted one or more mandatory consents."""

    status_code = 403
    error_code = "consent_required"


class NotFoundError(AppError):
    status_code = 404
    error_code = "not_found"
```

- [ ] **Step 3: Create `src/services/auth.py`**

```python
"""JWT decode + claim extraction. Pure function, no DB access."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import jwt
from jwt.exceptions import InvalidTokenError

from src.config import Settings
from src.exceptions import AuthError


@dataclass(frozen=True)
class AuthedUser:
    """Decoded JWT claims relevant to the app."""

    user_id: UUID
    email: str | None
    role: str  # 'authenticated' for normal users; 'service_role' for backend


def decode_jwt(token: str, settings: Settings) -> AuthedUser:
    """Verify signature, claims, and return an AuthedUser.

    Raises AuthError if anything is wrong: bad signature, expired, wrong audience,
    wrong issuer, missing `sub` claim.
    """
    try:
        claims = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience=settings.supabase_jwt_audience,
            issuer=settings.supabase_jwt_issuer,
            options={"require": ["exp", "sub", "aud", "iss"]},
        )
    except InvalidTokenError as e:
        raise AuthError(f"Invalid JWT: {e}") from e

    sub = claims.get("sub")
    if not sub:
        raise AuthError("JWT missing 'sub' claim")
    try:
        user_id = UUID(sub)
    except ValueError as e:
        raise AuthError(f"JWT 'sub' claim is not a UUID: {sub}") from e

    return AuthedUser(
        user_id=user_id,
        email=claims.get("email"),
        role=claims.get("role", "authenticated"),
    )
```

- [ ] **Step 4: Write the unit tests**

Path: `c:/gold-leaf-resume/apps/api/tests/test_auth_service.py`

```python
"""Unit tests for src.services.auth.decode_jwt."""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from src.config import Settings
from src.exceptions import AuthError
from src.services.auth import decode_jwt

TEST_SECRET = "test-jwt-secret-for-unit-tests-at-least-32-chars-please"
TEST_AUDIENCE = "authenticated"
TEST_ISSUER = "http://test/auth/v1"


def _settings() -> Settings:
    return Settings(  # type: ignore[call-arg]
        database_url="postgresql+asyncpg://x/x",
        supabase_url="http://test",
        supabase_anon_key="anon",
        supabase_service_role_key="service",
        supabase_jwt_secret=TEST_SECRET,
        supabase_jwt_audience=TEST_AUDIENCE,
        supabase_jwt_issuer=TEST_ISSUER,
    )


def _make_token(claims: dict) -> str:
    return jwt.encode(claims, TEST_SECRET, algorithm="HS256")


def test_decode_valid_token_returns_authed_user() -> None:
    user_id = uuid.uuid4()
    now = int(time.time())
    token = _make_token(
        {
            "sub": str(user_id),
            "email": "test@example.com",
            "aud": TEST_AUDIENCE,
            "iss": TEST_ISSUER,
            "exp": now + 3600,
            "iat": now,
            "role": "authenticated",
        }
    )
    user = decode_jwt(token, _settings())
    assert user.user_id == user_id
    assert user.email == "test@example.com"
    assert user.role == "authenticated"


def test_decode_expired_token_raises() -> None:
    token = _make_token(
        {
            "sub": str(uuid.uuid4()),
            "aud": TEST_AUDIENCE,
            "iss": TEST_ISSUER,
            "exp": int(time.time()) - 60,
        }
    )
    with pytest.raises(AuthError, match="Invalid JWT"):
        decode_jwt(token, _settings())


def test_decode_wrong_audience_raises() -> None:
    token = _make_token(
        {
            "sub": str(uuid.uuid4()),
            "aud": "anon",
            "iss": TEST_ISSUER,
            "exp": int(time.time()) + 3600,
        }
    )
    with pytest.raises(AuthError):
        decode_jwt(token, _settings())


def test_decode_wrong_issuer_raises() -> None:
    token = _make_token(
        {
            "sub": str(uuid.uuid4()),
            "aud": TEST_AUDIENCE,
            "iss": "http://attacker/auth/v1",
            "exp": int(time.time()) + 3600,
        }
    )
    with pytest.raises(AuthError):
        decode_jwt(token, _settings())


def test_decode_wrong_secret_raises() -> None:
    bad_token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "aud": TEST_AUDIENCE,
            "iss": TEST_ISSUER,
            "exp": int(time.time()) + 3600,
        },
        "wrong-secret-also-32-characters-yes-it-is",
        algorithm="HS256",
    )
    with pytest.raises(AuthError):
        decode_jwt(bad_token, _settings())


def test_decode_missing_sub_raises() -> None:
    token = _make_token(
        {
            "aud": TEST_AUDIENCE,
            "iss": TEST_ISSUER,
            "exp": int(time.time()) + 3600,
        }
    )
    with pytest.raises(AuthError):
        decode_jwt(token, _settings())


def test_decode_non_uuid_sub_raises() -> None:
    token = _make_token(
        {
            "sub": "not-a-uuid",
            "aud": TEST_AUDIENCE,
            "iss": TEST_ISSUER,
            "exp": int(time.time()) + 3600,
        }
    )
    with pytest.raises(AuthError, match="not a UUID"):
        decode_jwt(token, _settings())
```

- [ ] **Step 5: Run the tests**

```bash
cd c:/gold-leaf-resume/apps/api && uv run --env-file=.env pytest tests/test_auth_service.py -v
```
Expected: 7 passed.

- [ ] **Step 6: Commit**

```bash
cd c:/gold-leaf-resume && git add apps/api/src/services/ apps/api/src/exceptions.py apps/api/tests/test_auth_service.py
git commit -m "feat(api): add JWT decode service + AuthError + 7 unit tests"
```

---

## Task 5: Auth middleware + request_id middleware

**Files:**
- Create: `apps/api/src/middleware/__init__.py`
- Create: `apps/api/src/middleware/request_id.py`
- Create: `apps/api/src/middleware/auth.py`
- Modify: `apps/api/src/main.py`

- [ ] **Step 1: Create the middleware package**

```bash
cd c:/gold-leaf-resume/apps/api && mkdir -p src/middleware && touch src/middleware/__init__.py
```

- [ ] **Step 2: Create `src/middleware/request_id.py`**

```python
"""Attach a correlation ID to every request — usable by logs + Sentry."""
from __future__ import annotations

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Reads X-Request-ID header (or generates a new UUID4) and stores it
    in request.state + a ContextVar so structlog can pick it up."""

    async def dispatch(self, request: Request, call_next) -> Response:
        rid = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = rid
        token = request_id_ctx.set(rid)
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)
        response.headers["X-Request-ID"] = rid
        return response
```

- [ ] **Step 3: Create `src/middleware/auth.py`**

```python
"""JWT verification middleware.

Reads `Authorization: Bearer <jwt>` header. On success, attaches
`request.state.authed_user` (an AuthedUser) for downstream consumers.

Routes that should bypass auth (e.g. /healthz) are declared in PUBLIC_PATHS.
Routes that require auth raise 401 if no valid token is present.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.config import get_settings
from src.exceptions import AuthError
from src.services.auth import decode_jwt

# Paths that do not require auth.
PUBLIC_PATHS: frozenset[str] = frozenset(
    {
        "/",
        "/healthz",
        "/readyz",
        "/docs",
        "/openapi.json",
        "/redoc",
    }
)

# Path prefixes that do not require auth.
PUBLIC_PREFIXES: tuple[str, ...] = ("/webhooks/", "/static/")


def _is_public(path: str) -> bool:
    if path in PUBLIC_PATHS:
        return True
    return any(path.startswith(p) for p in PUBLIC_PREFIXES)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if _is_public(request.url.path):
            return await call_next(request)

        header = request.headers.get("authorization", "")
        if not header.lower().startswith("bearer "):
            return JSONResponse(
                status_code=401,
                content={"error": "unauthenticated", "message": "Missing Bearer token"},
            )

        token = header[7:]  # strip "Bearer "
        try:
            user = decode_jwt(token, get_settings())
        except AuthError as e:
            return JSONResponse(
                status_code=401,
                content={"error": e.error_code, "message": e.message},
            )

        request.state.authed_user = user
        return await call_next(request)
```

- [ ] **Step 4: Wire middleware into `main.py`**

Open `c:/gold-leaf-resume/apps/api/src/main.py` and replace its entire content with:

```python
"""FastAPI application factory."""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.db import dispose_db, init_db
from src.exceptions import AppError
from src.middleware.auth import AuthMiddleware
from src.middleware.request_id import RequestIDMiddleware


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Init DB on startup, dispose on shutdown."""
    await init_db()
    try:
        yield
    finally:
        await dispose_db()


app = FastAPI(
    title="Gold Leaf Resume API",
    version="0.0.0",
    description="Backend for Gold Leaf Resume. SP1·M2 — auth + consent middleware wired.",
    lifespan=lifespan,
)

# Middleware stack — outermost first. Starlette applies them in reverse, so the
# code order here is the request-side order: request_id → auth → routes.
app.add_middleware(AuthMiddleware)
app.add_middleware(RequestIDMiddleware)


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    """Map any AppError subclass to its declared HTTP status + JSON shape."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            **({"details": exc.details} if exc.details else {}),
        },
    )


@app.get("/healthz", tags=["health"])
async def healthz() -> dict[str, str]:
    """Liveness probe. Always returns 200 if the process is up."""
    return {"status": "ok"}
```

- [ ] **Step 5: Run the existing health + schema tests to confirm middleware doesn't break them**

```bash
cd c:/gold-leaf-resume/apps/api && uv run --env-file=.env pytest tests/test_health.py tests/test_schema.py -v
```
Expected: 4 passed.

If `test_healthz_returns_ok` fails: middleware is interfering. Check that `/healthz` is in PUBLIC_PATHS.

- [ ] **Step 6: Manual smoke (optional)**

```bash
cd c:/gold-leaf-resume/apps/api && uv run --env-file=.env uvicorn src.main:app --port 8000
```
In another shell:
```bash
curl -s http://127.0.0.1:8000/healthz       # expect {"status":"ok"}
curl -si http://127.0.0.1:8000/v1/me        # expect 401 with {"error":"unauthenticated",...}
```
Stop the server.

- [ ] **Step 7: Commit**

```bash
cd c:/gold-leaf-resume && git add apps/api/src/middleware/ apps/api/src/main.py
git commit -m "feat(api): add request_id + auth middleware; AppError exception handler"
```

---

## Task 6: Account auto-creation service + dependencies

**Files:**
- Create: `apps/api/src/services/accounts.py`
- Create: `apps/api/src/services/audit.py`
- Create: `apps/api/src/deps.py`

- [ ] **Step 1: Create `src/services/audit.py`**

```python
"""Append-only audit log writer."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.models import AuditLog


async def write_audit_log(
    session: AsyncSession,
    *,
    account_id: uuid.UUID | None,
    actor_user_id: uuid.UUID | None,
    event: str,
    extra: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """Insert one audit_log row. The session must be committed by the caller."""
    row = AuditLog(
        account_id=account_id,
        actor_user_id=actor_user_id,
        event=event,
        extra=extra or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    session.add(row)
    await session.flush()
    return row
```

- [ ] **Step 2: Create `src/services/accounts.py`**

```python
"""Account lifecycle — lazy-create on first authed request."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Account, AccountUser, Profile, Subscription, UsageMeter
from src.services.audit import write_audit_log


async def ensure_account(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    email: str | None,
) -> Account:
    """Return the user's account, creating it if it doesn't exist.

    On first call for a given user_id, creates:
    - accounts row (plan_id='free', region='au')
    - account_users row (role='owner')
    - profiles row (display_name = email's local part)
    - subscriptions row (plan_id='free', status='active')
    - usage_meters row (zeros)
    - audit_log row (event='account.created')

    Idempotent: subsequent calls for the same user_id return the existing account.
    """
    # Find existing account via account_users join.
    result = await session.execute(
        select(Account)
        .join(AccountUser, AccountUser.account_id == Account.id)
        .where(AccountUser.user_id == user_id)
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing

    # Create everything.
    account = Account()  # plan_id, region, etc. default
    session.add(account)
    await session.flush()

    session.add(AccountUser(account_id=account.id, user_id=user_id, role="owner"))
    session.add(
        Profile(
            user_id=user_id,
            display_name=(email.split("@")[0] if email else None),
        )
    )
    session.add(Subscription(account_id=account.id, plan_id="free", status="active"))
    session.add(UsageMeter(account_id=account.id))

    await write_audit_log(
        session,
        account_id=account.id,
        actor_user_id=user_id,
        event="account.created",
        extra={"email": email} if email else {},
    )

    await session.flush()
    return account
```

- [ ] **Step 3: Create `src/deps.py`**

```python
"""FastAPI dependencies used by route handlers."""
from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import session_scope
from src.exceptions import AuthError
from src.models import Account
from src.services.accounts import ensure_account
from src.services.auth import AuthedUser


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yields an async session in a transaction (commits on success)."""
    async with session_scope() as session:
        yield session


def current_user(request: Request) -> AuthedUser:
    """Return the AuthedUser attached by AuthMiddleware. Raises if missing."""
    user: AuthedUser | None = getattr(request.state, "authed_user", None)
    if user is None:
        # This should not happen for routes that are gated by AuthMiddleware,
        # but defensive: explicit error beats silent None.
        raise AuthError("No authenticated user on request — route not auth-gated?")
    return user


async def current_account(
    user: AuthedUser = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> Account:
    """Return the user's account, lazy-creating on first call."""
    return await ensure_account(db, user_id=user.user_id, email=user.email)
```

- [ ] **Step 4: Commit**

```bash
cd c:/gold-leaf-resume && git add apps/api/src/services/accounts.py apps/api/src/services/audit.py apps/api/src/deps.py
git commit -m "feat(api): add account auto-creation + audit log service + FastAPI deps"
```

---

## Task 7: GET /v1/me endpoint

**Files:**
- Create: `apps/api/src/schemas/__init__.py`
- Create: `apps/api/src/schemas/me.py`
- Create: `apps/api/src/routes/__init__.py`
- Create: `apps/api/src/routes/v1/__init__.py`
- Create: `apps/api/src/routes/v1/me.py`
- Modify: `apps/api/src/main.py`
- Create: `apps/api/tests/test_me_endpoint.py`

- [ ] **Step 1: Create the package skeletons**

```bash
cd c:/gold-leaf-resume/apps/api && mkdir -p src/schemas src/routes/v1 && \
  touch src/schemas/__init__.py src/routes/__init__.py src/routes/v1/__init__.py
```

- [ ] **Step 2: Create `src/schemas/me.py`**

```python
"""Pydantic response schemas for /v1/me."""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

REQUIRED_CONSENT_KINDS: frozenset[str] = frozenset({"tos", "privacy_policy", "sensitive_data_au"})


class ConsentStatus(BaseModel):
    """Per-kind consent state for the current user."""

    tos: bool = Field(description="Granted Terms of Service.")
    privacy_policy: bool = Field(description="Granted Privacy Policy.")
    sensitive_data_au: bool = Field(description="Granted AU sensitive-data consent.")
    marketing_email: bool = Field(description="Opted in to marketing email (optional).")


class MeResponse(BaseModel):
    """Response shape for GET /v1/me."""

    user_id: UUID
    account_id: UUID
    email: str | None
    plan_id: str
    region: str
    consent_status: ConsentStatus
```

- [ ] **Step 3: Create `src/routes/v1/me.py`**

```python
"""GET /v1/me — returns the authed user + their account + consent state."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.deps import current_account, current_user, get_db
from src.models import Account
from src.schemas.me import ConsentStatus, MeResponse
from src.services.auth import AuthedUser
from src.services.consent import get_consent_status

router = APIRouter(prefix="/v1/me", tags=["me"])


@router.get("", response_model=MeResponse)
async def get_me(
    user: AuthedUser = Depends(current_user),
    account: Account = Depends(current_account),
    db: AsyncSession = Depends(get_db),
) -> MeResponse:
    """Return identity + account + consent state for the authed user."""
    consent_status_dict = await get_consent_status(db, user_id=user.user_id)
    return MeResponse(
        user_id=user.user_id,
        account_id=account.id,
        email=user.email,
        plan_id=account.plan_id,
        region=account.region,
        consent_status=ConsentStatus(**consent_status_dict),
    )
```

NOTE: this imports `get_consent_status` from `src.services.consent` which we create in Task 8. The route won't import until Task 8 is done — that's expected.

- [ ] **Step 4: Modify `src/main.py` to register the router**

In `c:/gold-leaf-resume/apps/api/src/main.py`, add the import + `include_router` call. After the existing imports add:
```python
from src.routes.v1 import me as me_routes
```

After `app = FastAPI(...)` and middleware setup, before `@app.exception_handler`, add:
```python
app.include_router(me_routes.router)
```

The complete file should now look like:
```python
"""FastAPI application factory."""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.db import dispose_db, init_db
from src.exceptions import AppError
from src.middleware.auth import AuthMiddleware
from src.middleware.request_id import RequestIDMiddleware
from src.routes.v1 import me as me_routes


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    await init_db()
    try:
        yield
    finally:
        await dispose_db()


app = FastAPI(
    title="Gold Leaf Resume API",
    version="0.0.0",
    description="Backend for Gold Leaf Resume. SP1·M2 — auth + consent middleware wired.",
    lifespan=lifespan,
)

app.add_middleware(AuthMiddleware)
app.add_middleware(RequestIDMiddleware)

app.include_router(me_routes.router)


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            **({"details": exc.details} if exc.details else {}),
        },
    )


@app.get("/healthz", tags=["health"])
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
```

(Module imports `src.services.consent` indirectly — that lands in Task 8. Until then the module won't import and tests will fail. We commit Task 7 + Task 8 together at the end of T8 to avoid a broken interim state.)

- [ ] **Step 5: Write the `/v1/me` integration tests (won't pass until T8 lands consent service)**

Path: `c:/gold-leaf-resume/apps/api/tests/test_me_endpoint.py`

```python
"""Integration tests for GET /v1/me."""
from __future__ import annotations

import time
import uuid

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from src.main import app
from src.models import Account, AccountUser, Profile, Subscription, UsageMeter

TEST_SECRET = "super-secret-jwt-token-with-at-least-32-characters-long"


def _make_jwt(*, user_id: uuid.UUID, email: str, expires_in: int = 3600) -> str:
    """Sign a JWT with the test secret matching the local Supabase default."""
    now = int(time.time())
    return jwt.encode(
        {
            "sub": str(user_id),
            "email": email,
            "aud": "authenticated",
            "iss": "http://127.0.0.1:54321/auth/v1",
            "exp": now + expires_in,
            "iat": now,
            "role": "authenticated",
        },
        TEST_SECRET,
        algorithm="HS256",
    )


@pytest.mark.asyncio
async def test_me_returns_401_without_token() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/me")
    assert response.status_code == 401
    assert response.json()["error"] == "unauthenticated"


@pytest.mark.asyncio
async def test_me_returns_401_with_bad_signature() -> None:
    user_id = uuid.uuid4()
    now = int(time.time())
    bad_token = jwt.encode(
        {
            "sub": str(user_id),
            "aud": "authenticated",
            "iss": "http://127.0.0.1:54321/auth/v1",
            "exp": now + 3600,
        },
        "wrong-secret-also-32-characters-yes-it-is",
        algorithm="HS256",
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/me", headers={"Authorization": f"Bearer {bad_token}"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_lazy_creates_account_on_first_call(session) -> None:
    """First call for a new user_id creates account + dependents + audit row."""
    user_id = uuid.uuid4()
    email = f"test-{user_id}@example.com"
    token = _make_jwt(user_id=user_id, email=email)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/v1/me", headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == str(user_id)
    assert body["email"] == email
    assert body["plan_id"] == "free"
    assert body["region"] == "au"
    assert body["consent_status"] == {
        "tos": False,
        "privacy_policy": False,
        "sensitive_data_au": False,
        "marketing_email": False,
    }

    # Verify DB state (using the test's session — separate from the API request's session).
    account_id = uuid.UUID(body["account_id"])
    acct = (await session.execute(select(Account).where(Account.id == account_id))).scalar_one()
    assert acct.plan_id == "free"

    au = (
        await session.execute(
            select(AccountUser).where(AccountUser.account_id == account_id, AccountUser.user_id == user_id)
        )
    ).scalar_one()
    assert au.role == "owner"

    profile = (
        await session.execute(select(Profile).where(Profile.user_id == user_id))
    ).scalar_one()
    assert profile.display_name == email.split("@")[0]

    sub = (
        await session.execute(select(Subscription).where(Subscription.account_id == account_id))
    ).scalar_one()
    assert sub.plan_id == "free"
    assert sub.status == "active"

    meter = (
        await session.execute(select(UsageMeter).where(UsageMeter.account_id == account_id))
    ).scalar_one()
    assert meter.tokens_used == 0


@pytest.mark.asyncio
async def test_me_idempotent_on_second_call(session) -> None:
    """Second call for the same user returns the same account_id (no duplicate)."""
    user_id = uuid.uuid4()
    email = f"test-{user_id}@example.com"
    token = _make_jwt(user_id=user_id, email=email)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.get("/v1/me", headers={"Authorization": f"Bearer {token}"})
        r2 = await client.get("/v1/me", headers={"Authorization": f"Bearer {token}"})

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["account_id"] == r2.json()["account_id"]
```

NOTE on the `session` fixture: this is the SAME fixture from M1's `conftest.py`. Tests will use it to inspect DB state set by the API. Since the API uses its OWN session per request (via the lifespan-managed engine), the DB writes from the API will be visible to the test's session AFTER the API commits. The conftest fixture rolls back on teardown — this means any account/audit rows created by these tests will be cleaned up.

There's a subtle gotcha: the API request uses `session_scope()` which COMMITS on success. The test's `session` fixture uses an outer transaction that's rolled back at teardown. After the API commits, the test can see those rows; on teardown, the test's transaction rolls back but the API's committed rows are NOT touched. We need to clean them up explicitly.

For SP1·M2, accept this limitation: tests pollute the test DB with accounts. Address in a future test infrastructure refactor (M8 observability or earlier).

To minimize pollution in this test file, each test creates a fresh `user_id` (uuid.uuid4()), so subsequent tests don't conflict. Stale rows accumulate but don't break tests.

- [ ] **Step 6: Don't run tests yet — they'll fail until Task 8 lands consent service**

We commit T7 + T8 together at the end of T8 so the codebase doesn't have a broken interim state.

---

## Task 8: Consent service + endpoints + consent gate middleware

**Files:**
- Create: `apps/api/src/services/consent.py`
- Create: `apps/api/src/middleware/consent_gate.py`
- Create: `apps/api/src/schemas/consent.py`
- Create: `apps/api/src/routes/v1/consent.py`
- Modify: `apps/api/src/main.py`
- Create: `apps/api/tests/test_consent_flow.py`

- [ ] **Step 1: Create `src/services/consent.py`**

```python
"""Consent record lifecycle + status lookup."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import ConsentRecord
from src.schemas.me import REQUIRED_CONSENT_KINDS
from src.services.audit import write_audit_log

ALL_CONSENT_KINDS: tuple[str, ...] = (
    "tos",
    "privacy_policy",
    "sensitive_data_au",
    "marketing_email",
)


async def record_consent(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    account_id: uuid.UUID | None,
    kind: str,
    version: str,
    granted: bool,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ConsentRecord:
    """Insert one consent_records row + an audit_log row. Caller must commit."""
    if kind not in ALL_CONSENT_KINDS:
        raise ValueError(f"Unknown consent kind: {kind}")

    revoked_at = None if granted else datetime.now(timezone.utc)
    row = ConsentRecord(
        user_id=user_id,
        kind=kind,
        version=version,
        revoked_at=revoked_at,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    session.add(row)

    await write_audit_log(
        session,
        account_id=account_id,
        actor_user_id=user_id,
        event="consent.granted" if granted else "consent.revoked",
        extra={"kind": kind, "version": version},
        ip_address=ip_address,
        user_agent=user_agent,
    )

    await session.flush()
    return row


async def get_consent_status(
    session: AsyncSession, *, user_id: uuid.UUID
) -> dict[str, bool]:
    """Return {kind: granted_currently?} for every known consent kind.

    A consent is 'currently granted' if the most recent row for that (user_id, kind)
    has revoked_at IS NULL.
    """
    result = await session.execute(
        select(ConsentRecord)
        .where(ConsentRecord.user_id == user_id)
        .order_by(ConsentRecord.granted_at.desc())
    )
    rows = list(result.scalars().all())

    latest_by_kind: dict[str, ConsentRecord] = {}
    for row in rows:
        if row.kind not in latest_by_kind:
            latest_by_kind[row.kind] = row

    return {
        kind: (kind in latest_by_kind and latest_by_kind[kind].revoked_at is None)
        for kind in ALL_CONSENT_KINDS
    }


async def missing_mandatory_consents(
    session: AsyncSession, *, user_id: uuid.UUID
) -> list[str]:
    """Return the list of mandatory consent kinds NOT currently granted."""
    status = await get_consent_status(session, user_id=user_id)
    return [k for k in REQUIRED_CONSENT_KINDS if not status[k]]
```

- [ ] **Step 2: Create `src/middleware/consent_gate.py`**

```python
"""Consent gate middleware.

For routes that require an authed user, additionally enforce that all
mandatory consents (tos, privacy_policy, sensitive_data_au) are granted.

Allowlist routes that should bypass the gate (so the user CAN actually grant
consent without being blocked from doing so).
"""
from __future__ import annotations

# Routes that bypass the consent gate.
# These are paths the user MUST be able to call even without consent
# (otherwise they could never grant consent).
CONSENT_BYPASS_PATHS: frozenset[str] = frozenset(
    {
        "/v1/me",  # so user can see what consents they're missing
    }
)

CONSENT_BYPASS_PREFIXES: tuple[str, ...] = (
    "/v1/me/consent",  # POST grant + GET log
)


def consent_required_for_path(path: str) -> bool:
    """Return True if the given path requires consent before access."""
    if path in CONSENT_BYPASS_PATHS:
        return False
    if any(path.startswith(p) for p in CONSENT_BYPASS_PREFIXES):
        return False
    return path.startswith("/v1/")
```

Note: The CONSENT gate is implemented as a FastAPI dependency rather than a Starlette middleware. Reason: the gate needs a DB session to query consent state — that's much easier in a dependency than in middleware. The dependency `require_consent_granted` is exported from `src/deps.py` and added to route definitions or sub-routers that need gating. SP2+ uses `Depends(require_consent_granted)` on each gated endpoint.

Update `src/deps.py` — add this dependency at the bottom:

```python
from src.middleware.consent_gate import consent_required_for_path
from src.services.consent import missing_mandatory_consents


async def require_consent_granted(
    request: Request,
    user: AuthedUser = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Raise ConsentRequired if the user has not granted all mandatory consents.

    Routes opt in by adding `Depends(require_consent_granted)` to their signature.
    """
    if not consent_required_for_path(request.url.path):
        return
    missing = await missing_mandatory_consents(db, user_id=user.user_id)
    if missing:
        from src.exceptions import ConsentRequired
        raise ConsentRequired(
            "Missing mandatory consents",
            details={"missing": missing},
        )
```

- [ ] **Step 3: Create `src/schemas/consent.py`**

```python
"""Pydantic request/response schemas for consent endpoints."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.services.consent import ALL_CONSENT_KINDS


class ConsentGrantRequest(BaseModel):
    """POST /v1/me/consent body."""

    kind: str = Field(description=f"One of: {', '.join(ALL_CONSENT_KINDS)}")
    version: str = Field(description="Version of the legal doc being consented to (e.g. '2026-05-18').")
    granted: bool = Field(description="True to grant; False to revoke.")


class ConsentRecordResponse(BaseModel):
    """Single consent record (for the log endpoint)."""

    id: UUID
    kind: str
    version: str
    granted_at: datetime
    revoked_at: datetime | None
```

- [ ] **Step 4: Create `src/routes/v1/consent.py`**

```python
"""POST /v1/me/consent + GET /v1/me/consent/log."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.deps import current_account, current_user, get_db
from src.models import Account, ConsentRecord
from src.schemas.consent import ConsentGrantRequest, ConsentRecordResponse
from src.services.auth import AuthedUser
from src.services.consent import record_consent

router = APIRouter(prefix="/v1/me/consent", tags=["consent"])


@router.post("", status_code=201, response_model=ConsentRecordResponse)
async def grant_consent(
    body: ConsentGrantRequest,
    request: Request,
    user: AuthedUser = Depends(current_user),
    account: Account = Depends(current_account),
    db: AsyncSession = Depends(get_db),
) -> ConsentRecordResponse:
    """Record one consent decision. Always succeeds for known kinds."""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    row = await record_consent(
        db,
        user_id=user.user_id,
        account_id=account.id,
        kind=body.kind,
        version=body.version,
        granted=body.granted,
        ip_address=ip,
        user_agent=ua,
    )
    return ConsentRecordResponse(
        id=row.id,
        kind=row.kind,
        version=row.version,
        granted_at=row.granted_at,
        revoked_at=row.revoked_at,
    )


@router.get("/log", response_model=list[ConsentRecordResponse])
async def get_consent_log(
    user: AuthedUser = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ConsentRecordResponse]:
    """Return every consent record for the authed user (immutable history)."""
    result = await db.execute(
        select(ConsentRecord)
        .where(ConsentRecord.user_id == user.user_id)
        .order_by(ConsentRecord.granted_at.desc())
    )
    rows = result.scalars().all()
    return [
        ConsentRecordResponse(
            id=r.id,
            kind=r.kind,
            version=r.version,
            granted_at=r.granted_at,
            revoked_at=r.revoked_at,
        )
        for r in rows
    ]
```

- [ ] **Step 5: Register the consent router in `main.py`**

In `c:/gold-leaf-resume/apps/api/src/main.py`, add this import after the `me_routes` import:
```python
from src.routes.v1 import consent as consent_routes
```

And after `app.include_router(me_routes.router)`, add:
```python
app.include_router(consent_routes.router)
```

- [ ] **Step 6: Add consent enforcement to /v1/me's other endpoints**

For SP1·M2, `/v1/me` itself is NOT consent-gated (the user needs it to see what they're missing). The consent gate kicks in when SP2+ adds endpoints like `/v1/me/resumes`. For now, just verify the dependency is wired and ready.

To test the gate works, add ONE example gated route to demonstrate. Update `apps/api/src/routes/v1/me.py` to add:

```python
@router.get("/whoami", response_model=MeResponse)
async def whoami(
    _consent: None = Depends(require_consent_granted),
    user: AuthedUser = Depends(current_user),
    account: Account = Depends(current_account),
    db: AsyncSession = Depends(get_db),
) -> MeResponse:
    """Like /v1/me but gated by consent. Test target for consent_gate."""
    consent_status_dict = await get_consent_status(db, user_id=user.user_id)
    return MeResponse(
        user_id=user.user_id,
        account_id=account.id,
        email=user.email,
        plan_id=account.plan_id,
        region=account.region,
        consent_status=ConsentStatus(**consent_status_dict),
    )
```

And add `from src.deps import require_consent_granted` to the imports at the top of `me.py`.

- [ ] **Step 7: Write the consent-flow integration tests**

Path: `c:/gold-leaf-resume/apps/api/tests/test_consent_flow.py`

```python
"""Integration tests for POST/GET /v1/me/consent and the consent gate."""
from __future__ import annotations

import time
import uuid

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app

TEST_SECRET = "super-secret-jwt-token-with-at-least-32-characters-long"


def _make_jwt(user_id: uuid.UUID, email: str = "consent-test@example.com") -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "sub": str(user_id),
            "email": email,
            "aud": "authenticated",
            "iss": "http://127.0.0.1:54321/auth/v1",
            "exp": now + 3600,
            "iat": now,
            "role": "authenticated",
        },
        TEST_SECRET,
        algorithm="HS256",
    )


@pytest.mark.asyncio
async def test_post_consent_records_grant_and_returns_row() -> None:
    user_id = uuid.uuid4()
    token = _make_jwt(user_id)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First /me to lazy-create account.
        me = await client.get("/v1/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200

        response = await client.post(
            "/v1/me/consent",
            headers={"Authorization": f"Bearer {token}"},
            json={"kind": "tos", "version": "2026-05-18", "granted": True},
        )
    assert response.status_code == 201
    body = response.json()
    assert body["kind"] == "tos"
    assert body["version"] == "2026-05-18"
    assert body["revoked_at"] is None


@pytest.mark.asyncio
async def test_get_consent_log_returns_records_newest_first() -> None:
    user_id = uuid.uuid4()
    token = _make_jwt(user_id)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get("/v1/me", headers={"Authorization": f"Bearer {token}"})
        await client.post(
            "/v1/me/consent",
            headers={"Authorization": f"Bearer {token}"},
            json={"kind": "tos", "version": "2026-05-18", "granted": True},
        )
        await client.post(
            "/v1/me/consent",
            headers={"Authorization": f"Bearer {token}"},
            json={"kind": "privacy_policy", "version": "2026-05-18", "granted": True},
        )

        response = await client.get(
            "/v1/me/consent/log",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200
    log = response.json()
    assert len(log) == 2
    assert log[0]["kind"] == "privacy_policy"
    assert log[1]["kind"] == "tos"


@pytest.mark.asyncio
async def test_consent_gate_blocks_when_mandatory_missing() -> None:
    """GET /v1/me/whoami returns 403 when tos/privacy/sensitive_data_au not granted."""
    user_id = uuid.uuid4()
    token = _make_jwt(user_id)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get("/v1/me", headers={"Authorization": f"Bearer {token}"})
        response = await client.get(
            "/v1/me/whoami",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 403
    body = response.json()
    assert body["error"] == "consent_required"
    missing = set(body["details"]["missing"])
    assert missing == {"tos", "privacy_policy", "sensitive_data_au"}


@pytest.mark.asyncio
async def test_consent_gate_passes_after_all_mandatory_granted() -> None:
    user_id = uuid.uuid4()
    token = _make_jwt(user_id)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get("/v1/me", headers={"Authorization": f"Bearer {token}"})
        for kind in ("tos", "privacy_policy", "sensitive_data_au"):
            r = await client.post(
                "/v1/me/consent",
                headers={"Authorization": f"Bearer {token}"},
                json={"kind": kind, "version": "2026-05-18", "granted": True},
            )
            assert r.status_code == 201

        response = await client.get(
            "/v1/me/whoami",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["consent_status"]["tos"] is True
    assert body["consent_status"]["privacy_policy"] is True
    assert body["consent_status"]["sensitive_data_au"] is True


@pytest.mark.asyncio
async def test_revoke_consent_re_blocks_gate() -> None:
    user_id = uuid.uuid4()
    token = _make_jwt(user_id)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get("/v1/me", headers={"Authorization": f"Bearer {token}"})
        for kind in ("tos", "privacy_policy", "sensitive_data_au"):
            await client.post(
                "/v1/me/consent",
                headers={"Authorization": f"Bearer {token}"},
                json={"kind": kind, "version": "2026-05-18", "granted": True},
            )

        # Verify gate is open.
        ok = await client.get("/v1/me/whoami", headers={"Authorization": f"Bearer {token}"})
        assert ok.status_code == 200

        # Revoke one.
        await client.post(
            "/v1/me/consent",
            headers={"Authorization": f"Bearer {token}"},
            json={"kind": "tos", "version": "2026-05-18", "granted": False},
        )

        # Gate should re-block.
        blocked = await client.get("/v1/me/whoami", headers={"Authorization": f"Bearer {token}"})
    assert blocked.status_code == 403
    assert "tos" in blocked.json()["details"]["missing"]
```

- [ ] **Step 8: Run all tests**

Make sure Supabase is running and `apps/api/.env` has the correct `SUPABASE_JWT_SECRET` (the well-known local default).

```bash
cd c:/gold-leaf-resume/apps/api && uv run --env-file=.env pytest -v
```

Expected:
- 1 from test_health
- 3 from test_schema
- 7 from test_auth_service (Task 4)
- ≥4 from test_me_endpoint (Task 7)
- 5 from test_consent_flow (Task 8)

≈20 tests, all passing.

- [ ] **Step 9: Commit T7 + T8 together**

```bash
cd c:/gold-leaf-resume && git add apps/api/src/schemas/ apps/api/src/routes/ apps/api/src/services/consent.py apps/api/src/middleware/consent_gate.py apps/api/src/deps.py apps/api/src/main.py apps/api/tests/test_me_endpoint.py apps/api/tests/test_consent_flow.py
git commit -m "feat(api): add /v1/me + /v1/me/consent endpoints + consent gate dependency"
```

---

## Task 9: Test fixtures hardening — clean per-test API state

**Files:**
- Modify: `apps/api/tests/conftest.py`

The Task 7-8 tests rely on each test creating a fresh `user_id` so they don't conflict. That works but accumulates rows. Add a session-scoped autouse fixture that truncates app-data tables BEFORE the test session starts (preserves alembic_version + plans seed).

- [ ] **Step 1: Add the fixture**

Open `c:/gold-leaf-resume/apps/api/tests/conftest.py` and append:

```python
@pytest_asyncio.fixture(scope="session", autouse=True)
async def _clean_db_before_session(engine):
    """Truncate app-data tables before the test session starts.

    Preserves `plans` (seeded) and `alembic_version` (migration state).
    Runs ONCE per pytest invocation. Per-test rollback (in the `session` fixture)
    handles in-test isolation; this fixture handles cross-run accumulation.
    """
    async with engine.begin() as conn:
        from sqlalchemy import text
        # Order matters for FKs; truncate cascade is simpler.
        await conn.execute(
            text(
                """
                TRUNCATE TABLE
                  outcomes, applications, cover_letters, jds, resume_versions, resumes,
                  files, linkedin_imports, llm_keys, audit_log, consent_records,
                  usage_events, billing_events, usage_meters, subscriptions, profiles,
                  account_users, accounts, deleted_account_log
                RESTART IDENTITY CASCADE
                """
            )
        )
    yield
    # No teardown — we don't truncate after the session in case the user wants to inspect.
```

- [ ] **Step 2: Re-run the full test suite to confirm cleanliness**

```bash
cd c:/gold-leaf-resume/apps/api && uv run --env-file=.env pytest -v
```
Expected: ~20 tests pass, no leftover data conflicts.

- [ ] **Step 3: Commit**

```bash
cd c:/gold-leaf-resume && git add apps/api/tests/conftest.py
git commit -m "test(api): truncate app-data tables before each test session"
```

---

## Task 10: Generate OpenAPI types into `packages/shared-types`

**Files:**
- Modify: `packages/shared-types/package.json` (script to regenerate)
- Create: `packages/shared-types/src/openapi.ts` (generated)
- Modify: `packages/shared-types/src/index.ts`

- [ ] **Step 1: Add `openapi-typescript` as a devDep to shared-types**

Edit `c:/gold-leaf-resume/packages/shared-types/package.json` to add:

```json
{
  "name": "@goldleafresume/shared-types",
  "version": "0.0.0",
  "private": true,
  "type": "module",
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "exports": {
    ".": "./src/index.ts"
  },
  "scripts": {
    "generate": "openapi-typescript http://127.0.0.1:8000/openapi.json -o ./src/openapi.ts"
  },
  "devDependencies": {
    "openapi-typescript": "7.4.4"
  }
}
```

- [ ] **Step 2: Install + generate**

```bash
cd c:/gold-leaf-resume && pnpm install
```

Start the API in another terminal (or background):
```bash
cd c:/gold-leaf-resume/apps/api && uv run --env-file=.env uvicorn src.main:app --port 8000 &
sleep 3
cd c:/gold-leaf-resume/packages/shared-types && pnpm generate
```

Then kill the uvicorn process.

The generated `c:/gold-leaf-resume/packages/shared-types/src/openapi.ts` should contain types for `/v1/me`, `/v1/me/consent`, `/v1/me/consent/log`, plus all the schema types.

- [ ] **Step 3: Update `src/index.ts` to re-export the generated types**

```typescript
// Gold Leaf Resume — TypeScript types generated from FastAPI's OpenAPI schema.
// Regenerate via: `pnpm --filter @goldleafresume/shared-types generate`
// (requires the API to be running on http://127.0.0.1:8000)

export * from "./openapi";
```

- [ ] **Step 4: Add a workspace script**

In root `c:/gold-leaf-resume/package.json`, add to scripts:

```json
"types:generate": "pnpm --filter @goldleafresume/shared-types generate"
```

- [ ] **Step 5: Verify typecheck still passes**

```bash
cd c:/gold-leaf-resume && pnpm typecheck
```
Expected: clean.

- [ ] **Step 6: Commit**

```bash
cd c:/gold-leaf-resume && git add packages/shared-types/ package.json pnpm-lock.yaml
git commit -m "feat(types): generate TS types from FastAPI OpenAPI into shared-types"
```

---

## Task 11: Update CI — expand `migration-check` to exercise auth-flow tests

**Files:**
- Modify: `.github/workflows/test.yml`

The `migration-check` job already runs `pytest tests/test_schema.py`. Expand it to also run the new auth + consent tests (which need a DB + JWT secret).

- [ ] **Step 1: Update the workflow**

In `c:/gold-leaf-resume/.github/workflows/test.yml`, locate the `migration-check` job's `env:` block and add the JWT secret:

```yaml
    env:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/postgres
      SUPABASE_URL: http://127.0.0.1:54321
      SUPABASE_ANON_KEY: anon-test
      SUPABASE_SERVICE_ROLE_KEY: service-test
      SUPABASE_JWT_SECRET: super-secret-jwt-token-with-at-least-32-characters-long
      SUPABASE_JWT_AUDIENCE: authenticated
      SUPABASE_JWT_ISSUER: http://127.0.0.1:54321/auth/v1
```

Replace the existing "Run schema smoke tests" step with one that runs all DB-backed tests:

```yaml
      - name: Run all DB-backed tests
        run: uv run pytest tests/test_schema.py tests/test_me_endpoint.py tests/test_consent_flow.py -v
```

- [ ] **Step 2: Commit**

```bash
cd c:/gold-leaf-resume && git add .github/workflows/test.yml
git commit -m "ci: expand migration-check to exercise /v1/me + consent flow tests"
```

---

## Task 12: PR + merge

**Files:** None modified.

- [ ] **Step 1: Push the branch**

```bash
cd c:/gold-leaf-resume && git push -u origin m2-backend-auth-consent
```

- [ ] **Step 2: Open the PR**

```bash
cd c:/gold-leaf-resume && gh pr create \
  --title "SP1·M2 — Backend auth + consent middleware" \
  --base main \
  --head m2-backend-auth-consent \
  --body "$(cat <<'EOF'
## Summary
- JWT verification middleware: decodes Supabase HS256-signed tokens, attaches AuthedUser to request.state
- Account auto-creation on first authed request — accounts + account_users + profiles + subscriptions + usage_meters + audit_log row, all in one transaction
- `GET /v1/me` returns identity + account + consent state
- `POST /v1/me/consent` records consent grants/revokes (immutable append-only); `GET /v1/me/consent/log` returns history
- Consent gate dependency (`Depends(require_consent_granted)`) — opt-in per route; blocks with 403 + `{error: consent_required, details: {missing: [...]}}`
- Demo route `GET /v1/me/whoami` shows the gate in action
- `audit_log` writes on `account.created`, `consent.granted`, `consent.revoked`
- Generated TypeScript types in `packages/shared-types/src/openapi.ts` (regen via `pnpm types:generate`)
- M1 followup: model `server_default` cleanup using `sa.text()` (prevents Alembic autogen quoting bug recurrence)
- CI `migration-check` job expanded to run the full auth-flow integration tests

## Test plan
- [x] 7 unit tests in `test_auth_service.py` cover decode happy path + 6 failure modes
- [x] `test_me_endpoint.py` covers 401-no-token, 401-bad-sig, lazy-create on first call, idempotent on second
- [x] `test_consent_flow.py` covers POST grant, GET log, gate-blocks-missing, gate-passes-after-grant, revoke-re-blocks
- [x] All DB-backed tests run in CI against ephemeral Postgres
- [x] Manual: POST a real Supabase-issued JWT to `/v1/me` and inspect Studio's auth + DB tabs

Reaches SP1·M2 demoable end-state §1-8.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 3: Wait for CI**

```bash
sleep 10 && gh pr checks --watch
```

If CI fails: read the error, fix locally, commit, push, re-watch. Do NOT skip steps.

- [ ] **Step 4: Squash-merge**

When CI is green:
```bash
gh pr merge --squash --delete-branch
```

- [ ] **Step 5: Pull squashed commit locally**

```bash
cd c:/gold-leaf-resume && git checkout main && git pull
```

---

## Task 13: Tag `sp1-m2` + update SP1 spec status

- [ ] **Step 1: Tag**

```bash
cd c:/gold-leaf-resume && git tag -a sp1-m2 -m "SP1·M2 — Backend auth + consent middleware. JWT verify, lazy account creation, /v1/me + /v1/me/consent endpoints, consent gate dependency, ~20 tests."
git push --tags
```

- [ ] **Step 2: Update SP1 spec status in `Brains_Resume_Skill`**

In `c:/Brains_Resume_Skill/docs/specs/2026-05-18-sp1-gold-leaf-resume-platform-foundation.md`, find:
```markdown
**Status:** In implementation — SP1·M0 + M1 complete (2026-05-18 — `sp1-m0` + `sp1-m1` tags in `gold-leaf-resume`); M2 (Backend auth + consent middleware) next.
```

Replace with:
```markdown
**Status:** In implementation — SP1·M0 + M1 + M2 complete (2026-05-18 — `sp1-m0`, `sp1-m1`, `sp1-m2` tags in `gold-leaf-resume`); M3 (Frontend auth + consent flows) next.
```

- [ ] **Step 3: Commit in Brains_Resume_Skill**

```bash
cd c:/Brains_Resume_Skill && git add docs/specs/2026-05-18-sp1-gold-leaf-resume-platform-foundation.md
git commit -m "docs: mark SP1·M2 complete in spec status"
git push
```

---

## Self-review

**Spec coverage (vs SP1 spec §4.7 + §5.1 + §5.3):**

| Spec section | M2 coverage |
|---|---|
| §4.7 Supabase Auth providers | ✗ Frontend wires in M3 — M2 is backend-only |
| §4.7 Required-before-use sequence | ✗ Partially — backend enforces consent gate; frontend flow in M3 |
| §4.7 Consent middleware | ✓ Task 8 — Depends(require_consent_granted) |
| §4.7 Session model (JWT verification) | ✓ Task 4 + Task 5 |
| §4.7 Consent revocation | ✓ Task 8 — `granted: false` records a revocation |
| §5.1 Account lazy-create | ✓ Task 6 |
| §5.1 Profile creation | ✓ Task 6 |
| §5.3 ConsentRecord writes | ✓ Task 8 |
| §5.3 AuditLog writes | ✓ Tasks 6 + 8 |
| §5.3 DeletedAccountLog | ✗ Deferred to M6 (Settings tab — delete account flow) |
| §7 require_plan decorator | ✗ Deferred to SP3 (when paid features get gated) |

**Placeholder scan:** searched for "TBD", "TODO", "implement later" — none.

**Type consistency check:** `AuthedUser` defined in `src.services.auth` and consumed in `src.deps`, `src.middleware.auth`, route modules — all match. `MeResponse` schema matches the route return type. `ConsentRecordResponse` field set matches the model fields used.

**Known shortcuts:**
- Tests pollute the dev DB across runs (truncate-once-per-session fixture cleans up at start). Acceptable for SP1; SP2+ may want per-test rollback for true isolation.
- The consent gate is a dependency, not a middleware. Reason: middleware has no easy access to a DB session. Side effect: every gated route must explicitly add `Depends(require_consent_granted)`. We could add a router-level dependency instead — defer.
- JWT verification is HS256 only. JWKS / RS256 support is a future enhancement for production where Supabase issues asymmetric keys.

**Pre-flight gotchas on execution:**
- The Supabase JWT secret discovery: if the well-known default doesn't decode real JWTs, the discovery methods in Open Prerequisites must succeed.
- `TestClient` may need `lifespan` triggered to init the DB engine — using `ASGITransport(app=app)` with `AsyncClient` directly does NOT trigger lifespan. The test fixture `engine` uses its own engine (not the app's), so the API and tests connect to the same DB but via separate pools — works fine.

---

**End of SP1·M2 plan.**
