# Gold Leaf Resume — SP1·M0: Monorepo Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the `shard-BRAINS/gold-leaf-resume` monorepo with a `pnpm` + `uv` workspace, an empty FastAPI service at `apps/api`, a "hello world" Next.js 15 app at `apps/web`, local Postgres via Docker Compose, lint/typecheck tooling for both languages, and a green GitHub Actions CI on PR. No DB schema, no auth, no real UI — just the runnable foundation that M1 (DB schema) plugs into.

**Architecture:** Top-level pnpm workspace (`apps/*`, `packages/*`) for TypeScript, with `apps/api` managed independently by `uv` (Python). Three local processes via Docker Compose: Postgres 16 (used from M1 onward), the FastAPI service, the Next.js dev server. CI runs lint + typecheck + smoke tests on every PR; deployments come in M9.

**Tech Stack:** Next.js 15 (App Router, TypeScript strict), Tailwind CSS, shadcn/ui (deferred install until UI work), FastAPI, Pydantic v2, uvicorn, Python 3.12, pytest, Vitest, Biome, ruff, mypy, pnpm 9, uv, Docker Compose, GitHub Actions, pre-commit.

**Predecessor spec:** [docs/specs/2026-05-18-sp1-gold-leaf-resume-platform-foundation.md](../specs/2026-05-18-sp1-gold-leaf-resume-platform-foundation.md)

**Demoable end state:**
1. `pnpm dev --filter web` serves a Gold Leaf Resume hello page at `http://localhost:3000`.
2. `cd apps/api && uv run uvicorn src.main:app --reload` serves `GET /healthz` returning `{"status":"ok"}` at `http://localhost:8000/healthz`.
3. `docker compose up -d postgres` starts a Postgres 16 container; `psql` connects with seeded credentials.
4. `pnpm lint` and `pnpm typecheck` pass at the workspace root.
5. `cd apps/api && uv run pytest` passes the health smoke test.
6. `cd apps/api && uv run ruff check . && uv run mypy src` pass.
7. A PR opened against `main` triggers a green CI run.
8. Tag `sp1-m0` exists on `main`.

---

## File Structure

Files this milestone creates, grouped by directory. Each file has one clear responsibility.

```
gold-leaf-resume/                       NEW REPO — shard-BRAINS/gold-leaf-resume
├── .editorconfig                       Cross-IDE indent + EOL rules
├── .gitignore                          Node + Python + OS + IDE ignores
├── .pre-commit-config.yaml             Pre-commit hooks (biome, ruff, mypy)
├── .nvmrc                              Pin Node version
├── .python-version                     Pin Python version (for uv)
├── LICENSE                             MIT
├── README.md                           Quickstart + project layout
├── biome.json                          JS/TS lint + format config
├── docker-compose.yml                  Local Postgres
├── pnpm-workspace.yaml                 Declares apps/* + packages/* workspaces
├── package.json                        Root workspace manifest + dev scripts
├── pyproject.toml                      Root tool configs (ruff, mypy, pytest)
│
├── .github/
│   └── workflows/
│       └── test.yml                    PR CI: lint + typecheck + smoke tests
│
├── apps/
│   ├── api/
│   │   ├── pyproject.toml              FastAPI app deps (uv-managed)
│   │   ├── uv.lock                     Lockfile (generated)
│   │   ├── README.md                   How to run the API locally
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   └── main.py                 FastAPI app factory + /healthz route
│   │   └── tests/
│   │       ├── __init__.py
│   │       └── test_health.py          Smoke test for /healthz
│   │
│   └── web/
│       ├── package.json                Next.js + Tailwind + Vitest deps
│       ├── tsconfig.json               Strict TS
│       ├── next.config.mjs             Next config (minimal)
│       ├── tailwind.config.ts          Tailwind base
│       ├── postcss.config.mjs          PostCSS for Tailwind
│       ├── vitest.config.ts            Vitest config
│       ├── README.md                   How to run the web app locally
│       ├── app/
│       │   ├── layout.tsx              Root layout
│       │   ├── page.tsx                Hello page
│       │   └── globals.css             Tailwind directives
│       └── tests/
│           └── home.test.tsx           Smoke test for hello page
│
└── packages/
    ├── design-tokens/
    │   ├── package.json                Placeholder package
    │   └── src/index.ts                Empty exports (filled in M3)
    └── shared-types/
        ├── package.json                Placeholder package
        └── src/index.ts                Empty exports (filled in M2 from FastAPI OpenAPI)
```

**Why this layout:** files that change together live together. The `apps/api` Python project is self-contained (its own pyproject.toml, lockfile, tests) so `uv` manages it without dragging Node into the loop. Root `pyproject.toml` carries cross-cutting tool configs (ruff, mypy) that apply repo-wide. Root `package.json` only orchestrates pnpm scripts that delegate to workspaces.

---

## Open prerequisites (resolve before Task 1)

- [ ] **Confirm GitHub org/repo name.** Default: `shard-BRAINS/gold-leaf-resume`. If different, substitute throughout.
- [ ] **Confirm domain TLD.** Default working assumption: `goldleafresume.com.au`. M0 doesn't need DNS yet; flagged here so the README can reference it.
- [ ] **`gh` CLI authenticated** as a user with repo-create rights on `shard-BRAINS`.
- [ ] **Tools installed locally:** `pnpm` 9.x, `uv` 0.4+, `python` 3.12, `node` 20 LTS, Docker Desktop, `pre-commit`, `gh`.

---

## Task 1: Create the GitHub repo and clone locally

**Files:**
- None yet (this task creates the working directory)

- [ ] **Step 1: Create the GitHub repo (private to start; flip public at SP7)**

Run:
```bash
gh repo create shard-BRAINS/gold-leaf-resume \
  --private \
  --description "Gold Leaf Resume — cloud SaaS shard of BRAINS Incubator. ND-aware resume & application management." \
  --license MIT \
  --add-readme \
  --clone=false
```
Expected: `https://github.com/shard-BRAINS/gold-leaf-resume` exists.

- [ ] **Step 2: Clone into a sibling directory of the existing skill repo**

Run (from `c:\` on Windows or `~/Code/` on Mac/Linux — adjust as needed):
```bash
cd c:/
gh repo clone shard-BRAINS/gold-leaf-resume gold-leaf-resume
cd gold-leaf-resume
```
Expected: `c:\gold-leaf-resume\` exists, contains `README.md` + `LICENSE`.

- [ ] **Step 3: Configure local git identity (if not global)**

Run:
```bash
git config user.name "Matthew Charles Gell"
git config user.email "fenzeh@gmail.com"
```

- [ ] **Step 4: Verify branch is `main`**

Run:
```bash
git branch --show-current
```
Expected: `main`.

---

## Task 2: Add top-level workspace files

**Files:**
- Create: `c:/gold-leaf-resume/.gitignore`
- Create: `c:/gold-leaf-resume/.editorconfig`
- Create: `c:/gold-leaf-resume/.nvmrc`
- Create: `c:/gold-leaf-resume/.python-version`
- Create: `c:/gold-leaf-resume/pnpm-workspace.yaml`
- Create: `c:/gold-leaf-resume/package.json`
- Create: `c:/gold-leaf-resume/pyproject.toml`
- Modify: `c:/gold-leaf-resume/README.md` (overwrite the gh-generated one)

- [ ] **Step 1: Write `.gitignore`**

Content:
```gitignore
# Node
node_modules/
.pnpm-store/
.next/
.turbo/
dist/
build/
*.tsbuildinfo

# Python
__pycache__/
*.pyc
.venv/
.uv_cache/
.pytest_cache/
.mypy_cache/
.ruff_cache/
htmlcov/
.coverage
*.egg-info/

# Env files
.env
.env.local
.env.*.local
!.env.example

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
*.swp

# Docker volumes
docker-data/

# Generated
apps/web/.next/
apps/web/out/
packages/shared-types/src/generated/
```

- [ ] **Step 2: Write `.editorconfig`**

Content:
```ini
root = true

[*]
charset = utf-8
end_of_line = lf
indent_style = space
indent_size = 2
insert_final_newline = true
trim_trailing_whitespace = true

[*.py]
indent_size = 4

[*.md]
trim_trailing_whitespace = false

[Makefile]
indent_style = tab
```

- [ ] **Step 3: Write `.nvmrc`**

Content:
```
20.18.0
```

- [ ] **Step 4: Write `.python-version`**

Content:
```
3.12
```

- [ ] **Step 5: Write `pnpm-workspace.yaml`**

Content:
```yaml
packages:
  - "apps/*"
  - "packages/*"
```

- [ ] **Step 6: Write root `package.json`**

Content:
```json
{
  "name": "gold-leaf-resume",
  "version": "0.0.0",
  "private": true,
  "description": "Gold Leaf Resume — cloud SaaS shard of BRAINS Incubator",
  "license": "MIT",
  "packageManager": "pnpm@9.12.0",
  "engines": {
    "node": ">=20.0.0",
    "pnpm": ">=9.0.0"
  },
  "scripts": {
    "dev:web": "pnpm --filter web dev",
    "build": "pnpm --filter \"./apps/**\" --filter \"./packages/**\" -r build",
    "lint": "biome check .",
    "lint:fix": "biome check --write .",
    "format": "biome format --write .",
    "typecheck": "pnpm --filter web typecheck",
    "test": "pnpm --filter web test"
  },
  "devDependencies": {
    "@biomejs/biome": "1.9.4"
  }
}
```

- [ ] **Step 7: Write root `pyproject.toml`** (tool configs only — Python deps live in apps/api)

Content:
```toml
[tool.ruff]
line-length = 100
target-version = "py312"
extend-exclude = [".venv", "node_modules", ".next"]

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "N", "W", "C90", "RUF"]
ignore = ["E501"]  # handled by formatter

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["B011"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.mypy]
python_version = "3.12"
strict = true
pretty = true
show_error_codes = true
warn_unused_configs = true
plugins = ["pydantic.mypy"]

[[tool.mypy.overrides]]
module = ["uvicorn.*", "litellm.*"]
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["apps/api/tests"]
asyncio_mode = "auto"
addopts = "-ra --strict-markers"
```

- [ ] **Step 8: Overwrite root `README.md`**

Content:
```markdown
# Gold Leaf Resume

Cloud-hosted, ND-aware resume and job-application management. A shard product under [BRAINS Incubator](https://github.com/shard-BRAINS).

> **Status:** Pre-launch. SP1 (Platform Foundation) in active development. See [docs/specs/](docs/specs/) for the architecture spec and [docs/plans/](docs/plans/) for sub-project plans.

## Quickstart (local dev)

Prerequisites: pnpm 9, uv 0.4+, Python 3.12, Node 20 LTS, Docker.

```bash
# Install JS deps (workspace-wide)
pnpm install

# Install Python deps for the API
cd apps/api && uv sync && cd ../..

# Start Postgres
docker compose up -d postgres

# Run the API (terminal 1)
cd apps/api && uv run uvicorn src.main:app --reload --port 8000

# Run the web app (terminal 2)
pnpm dev:web
```

Then open <http://localhost:3000>.

## Layout

```
apps/
  api/          FastAPI service (Python 3.12)
  web/          Next.js 15 frontend (TypeScript)
packages/
  design-tokens/  Shared Tailwind tokens (Gold Leaf palette)
  shared-types/   TypeScript types generated from FastAPI OpenAPI
infra/          (future) Fly, Supabase, runbooks
docs/
  specs/        Architecture specs
  plans/        Implementation plans
```

## License

MIT. © BRAINS Incubator.
```

- [ ] **Step 9: Commit**

Run:
```bash
git add .gitignore .editorconfig .nvmrc .python-version pnpm-workspace.yaml package.json pyproject.toml README.md
git commit -m "chore: add monorepo workspace + tooling baseline"
```

---

## Task 3: Scaffold the FastAPI app at `apps/api`

**Files:**
- Create: `apps/api/pyproject.toml`
- Create: `apps/api/src/__init__.py` (empty)
- Create: `apps/api/src/main.py`
- Create: `apps/api/tests/__init__.py` (empty)
- Create: `apps/api/tests/test_health.py`
- Create: `apps/api/README.md`

- [ ] **Step 1: Create the directory structure**

Run:
```bash
mkdir -p apps/api/src apps/api/tests
```

- [ ] **Step 2: Write `apps/api/pyproject.toml`**

Content:
```toml
[project]
name = "gold-leaf-resume-api"
version = "0.0.0"
description = "Gold Leaf Resume — FastAPI backend"
requires-python = ">=3.12,<3.13"
dependencies = [
  "fastapi==0.115.6",
  "uvicorn[standard]==0.32.1",
  "pydantic==2.10.4",
  "pydantic-settings==2.7.0",
  "structlog==24.4.0",
  "httpx==0.28.1",
]

[dependency-groups]
dev = [
  "pytest==8.3.4",
  "pytest-asyncio==0.25.0",
  "pytest-cov==6.0.0",
  "ruff==0.8.4",
  "mypy==1.13.0",
  "types-requests",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src"]
```

- [ ] **Step 3: Write `apps/api/src/__init__.py`** (empty file — just `touch`)

Run:
```bash
echo "" > apps/api/src/__init__.py
```

- [ ] **Step 4: Sync dependencies with uv**

Run from `apps/api/`:
```bash
cd apps/api && uv sync && cd ../..
```
Expected: `apps/api/uv.lock` is created; `apps/api/.venv/` exists.

- [ ] **Step 5: Write `apps/api/tests/__init__.py`** (empty)

Run:
```bash
echo "" > apps/api/tests/__init__.py
```

- [ ] **Step 6: Write the failing test for `/healthz`**

Path: `apps/api/tests/test_health.py`

Content:
```python
"""Smoke test: /healthz returns 200 with status ok."""
from fastapi.testclient import TestClient

from src.main import app


def test_healthz_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 7: Run the test to verify it fails (no `src.main` yet)**

Run from `apps/api/`:
```bash
cd apps/api && uv run pytest tests/test_health.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'src.main'` or similar import error.

- [ ] **Step 8: Write the minimal FastAPI app**

Path: `apps/api/src/main.py`

Content:
```python
"""FastAPI application factory.

This module exposes the `app` ASGI callable consumed by uvicorn and tests.
"""
from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(
    title="Gold Leaf Resume API",
    version="0.0.0",
    description="Backend for Gold Leaf Resume. SP1·M0 baseline — only /healthz wired.",
)


@app.get("/healthz", tags=["health"])
async def healthz() -> dict[str, str]:
    """Liveness probe. Always returns 200 if the process is up."""
    return {"status": "ok"}
```

- [ ] **Step 9: Run the test to verify it passes**

Run from `apps/api/`:
```bash
cd apps/api && uv run pytest tests/test_health.py -v
```
Expected: PASS `1 passed`.

- [ ] **Step 10: Verify the dev server runs**

Run from `apps/api/`:
```bash
cd apps/api && uv run uvicorn src.main:app --port 8000
```
Then in another terminal:
```bash
curl -s http://localhost:8000/healthz
```
Expected: `{"status":"ok"}`. Stop the server with Ctrl+C.

- [ ] **Step 11: Write `apps/api/README.md`**

Content:
````markdown
# Gold Leaf Resume — API

FastAPI backend. Python 3.12, managed by `uv`.

## Run locally

```bash
uv sync
uv run uvicorn src.main:app --reload --port 8000
```

## Test

```bash
uv run pytest -v
```

## Lint + typecheck

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

## Layout

```
src/
  main.py        FastAPI app factory + route mounting
tests/
  test_*.py      pytest-based tests
```

## Notes

- All routes will live under `/v1/...` from M2 onward. `/healthz` and `/readyz` stay un-versioned.
- This is SP1·M0 baseline. No database, no auth, no real endpoints yet.
````

- [ ] **Step 12: Commit**

Run from repo root:
```bash
git add apps/api/
git commit -m "feat(api): scaffold FastAPI app with /healthz"
```

---

## Task 4: Scaffold the Next.js app at `apps/web`

**Files:**
- Create: `apps/web/package.json`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/next.config.mjs`
- Create: `apps/web/tailwind.config.ts`
- Create: `apps/web/postcss.config.mjs`
- Create: `apps/web/vitest.config.ts`
- Create: `apps/web/app/layout.tsx`
- Create: `apps/web/app/page.tsx`
- Create: `apps/web/app/globals.css`
- Create: `apps/web/tests/home.test.tsx`
- Create: `apps/web/README.md`

- [ ] **Step 1: Create the directory structure**

Run from repo root:
```bash
mkdir -p apps/web/app apps/web/tests
```

- [ ] **Step 2: Write `apps/web/package.json`**

Content:
```json
{
  "name": "web",
  "version": "0.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev --port 3000",
    "build": "next build",
    "start": "next start",
    "lint": "biome check .",
    "typecheck": "tsc --noEmit",
    "test": "vitest run"
  },
  "dependencies": {
    "next": "15.1.3",
    "react": "19.0.0",
    "react-dom": "19.0.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "6.6.3",
    "@testing-library/react": "16.1.0",
    "@types/node": "22.10.2",
    "@types/react": "19.0.2",
    "@types/react-dom": "19.0.2",
    "@vitejs/plugin-react": "4.3.4",
    "autoprefixer": "10.4.20",
    "jsdom": "25.0.1",
    "postcss": "8.4.49",
    "tailwindcss": "3.4.17",
    "typescript": "5.7.2",
    "vitest": "2.1.8"
  }
}
```

- [ ] **Step 3: Write `apps/web/tsconfig.json`**

Content:
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 4: Write `apps/web/next.config.mjs`**

Content:
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    typedRoutes: true,
  },
};

export default nextConfig;
```

- [ ] **Step 5: Write `apps/web/tailwind.config.ts`**

Content:
```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        goldleaf: {
          50: "#fdf9e7",
          100: "#fbf0c2",
          200: "#f6e07d",
          300: "#f0cf3a",
          400: "#e6b91f",
          500: "#c89a14",
          600: "#a37710",
          700: "#7f5a0d",
          800: "#5b400a",
          900: "#3c2a06",
        },
        cream: {
          50: "#fefcf6",
          100: "#fbf6e8",
          200: "#f4ecd0",
        },
        ink: {
          700: "#2a2522",
          800: "#1a1714",
          900: "#100e0c",
          950: "#080706",
        },
      },
    },
  },
  plugins: [],
};

export default config;
```

- [ ] **Step 6: Write `apps/web/postcss.config.mjs`**

Content:
```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 7: Write `apps/web/vitest.config.ts`**

Content:
```typescript
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/setup.ts"],
  },
});
```

- [ ] **Step 8: Write `apps/web/tests/setup.ts`**

Content:
```typescript
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 9: Write `apps/web/app/globals.css`**

Content:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  color-scheme: light dark;
}

html {
  font-family:
    ui-sans-serif,
    system-ui,
    -apple-system,
    BlinkMacSystemFont,
    "Segoe UI",
    Roboto,
    sans-serif;
}
```

- [ ] **Step 10: Write `apps/web/app/layout.tsx`**

Content:
```tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Gold Leaf Resume",
  description:
    "ND-aware resume and job-application management. A shard product under BRAINS Incubator.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="bg-cream-50 text-ink-900 dark:bg-ink-950 dark:text-cream-50">
      <body>{children}</body>
    </html>
  );
}
```

- [ ] **Step 11: Write the failing smoke test**

Path: `apps/web/tests/home.test.tsx`

Content:
```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Home from "../app/page";

describe("Home page", () => {
  it("renders the Gold Leaf Resume hello", () => {
    render(<Home />);
    expect(
      screen.getByRole("heading", { name: /gold leaf resume/i, level: 1 }),
    ).toBeInTheDocument();
  });

  it("includes BRAINS Incubator attribution", () => {
    render(<Home />);
    expect(screen.getByText(/brains incubator/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 12: Install workspace deps and run test (should fail — `page.tsx` doesn't exist)**

Run from repo root:
```bash
pnpm install
cd apps/web && pnpm test
```
Expected: FAIL — `Cannot find module '../app/page'` or `app/page.tsx` doesn't exist.

- [ ] **Step 13: Write `apps/web/app/page.tsx`**

Content:
```tsx
export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-6 py-12">
      <div className="max-w-2xl text-center">
        <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
          <span className="text-goldleaf-500">Gold Leaf</span> Resume
        </h1>
        <p className="mt-6 text-lg text-ink-700 dark:text-cream-100">
          ND-aware resume and job-application management. Currently in private development.
        </p>
        <p className="mt-12 text-sm text-ink-700/70 dark:text-cream-100/70">
          A shard product under <span className="font-medium">BRAINS Incubator</span>.
        </p>
      </div>
    </main>
  );
}
```

- [ ] **Step 14: Run the test to verify it passes**

Run from `apps/web/`:
```bash
cd apps/web && pnpm test
```
Expected: PASS `2 passed`.

- [ ] **Step 15: Verify the dev server runs**

Run from repo root:
```bash
pnpm dev:web
```
Open `http://localhost:3000`. Expected: see "Gold Leaf Resume" heading with the gold accent on "Gold Leaf". Stop with Ctrl+C.

- [ ] **Step 16: Write `apps/web/README.md`**

Content:
````markdown
# Gold Leaf Resume — Web

Next.js 15 (App Router, TypeScript strict) frontend.

## Run locally

```bash
# From repo root:
pnpm install
pnpm dev:web

# Or from this directory:
pnpm dev
```

Then open <http://localhost:3000>.

## Test

```bash
pnpm test            # Vitest unit/component tests
```

## Lint + typecheck

```bash
pnpm lint
pnpm typecheck
```

## Layout

```
app/
  layout.tsx     Root layout (HTML, body, fonts)
  page.tsx       Marketing-light landing (SP1·M0 hello)
  globals.css    Tailwind directives + base resets
tests/
  *.test.tsx     Vitest component tests
```

## Notes

- Dark mode opt-in via `class` strategy on `<html>`. SP1·M6 wires the user toggle.
- Gold Leaf palette defined in `tailwind.config.ts`. Future shared package: `packages/design-tokens`.
````

- [ ] **Step 17: Commit**

Run from repo root:
```bash
git add apps/web/ pnpm-lock.yaml
git commit -m "feat(web): scaffold Next.js hello page with Gold Leaf palette"
```

---

## Task 5: Add placeholder shared packages

**Files:**
- Create: `packages/design-tokens/package.json`
- Create: `packages/design-tokens/src/index.ts`
- Create: `packages/shared-types/package.json`
- Create: `packages/shared-types/src/index.ts`

- [ ] **Step 1: Create directories**

Run from repo root:
```bash
mkdir -p packages/design-tokens/src packages/shared-types/src
```

- [ ] **Step 2: Write `packages/design-tokens/package.json`**

Content:
```json
{
  "name": "@goldleafresume/design-tokens",
  "version": "0.0.0",
  "private": true,
  "type": "module",
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "exports": {
    ".": "./src/index.ts"
  }
}
```

- [ ] **Step 3: Write `packages/design-tokens/src/index.ts`**

Content:
```typescript
// Gold Leaf Resume — design tokens placeholder.
// Populated in SP1·M3 (frontend auth + consent flows) with the full Tailwind preset.
// For now, the Gold Leaf palette lives inline in apps/web/tailwind.config.ts.

export {};
```

- [ ] **Step 4: Write `packages/shared-types/package.json`**

Content:
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
  }
}
```

- [ ] **Step 5: Write `packages/shared-types/src/index.ts`**

Content:
```typescript
// Gold Leaf Resume — TypeScript types generated from FastAPI's OpenAPI schema.
// Populated in SP1·M2 (backend auth + consent middleware) via openapi-typescript-codegen.
// For now, this package is intentionally empty.

export {};
```

- [ ] **Step 6: Re-install to wire the new workspaces**

Run from repo root:
```bash
pnpm install
```
Expected: pnpm reports the two new packages added to the workspace.

- [ ] **Step 7: Commit**

Run:
```bash
git add packages/
git commit -m "chore: add design-tokens + shared-types placeholder packages"
```

---

## Task 6: Local Postgres via Docker Compose

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example` (top-level)

- [ ] **Step 1: Write `docker-compose.yml`**

Content:
```yaml
services:
  postgres:
    image: postgres:16-alpine
    container_name: goldleaf-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: goldleaf
      POSTGRES_PASSWORD: goldleaf_local_dev
      POSTGRES_DB: goldleaf
    ports:
      - "5432:5432"
    volumes:
      - goldleaf_pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U goldleaf -d goldleaf"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  goldleaf_pgdata:
    driver: local
```

- [ ] **Step 2: Write top-level `.env.example`**

Content:
```bash
# Gold Leaf Resume — local environment (top-level)
# Copy to .env for tools that read repo-root env (e.g. docker-compose) — never commit .env.

# Local Postgres (matches docker-compose.yml defaults)
DATABASE_URL=postgresql://goldleaf:goldleaf_local_dev@localhost:5432/goldleaf

# Per-app env files live in apps/api/.env and apps/web/.env.local — see those READMEs.
```

- [ ] **Step 3: Start Postgres**

Run from repo root:
```bash
docker compose up -d postgres
```
Expected: container `goldleaf-postgres` running.

- [ ] **Step 4: Verify Postgres is reachable**

Run:
```bash
docker compose exec postgres psql -U goldleaf -d goldleaf -c "SELECT version();"
```
Expected: a line like `PostgreSQL 16.x on x86_64-pc-linux-musl ...`.

- [ ] **Step 5: Verify the healthcheck**

Run:
```bash
docker compose ps
```
Expected: `goldleaf-postgres` status `Up (healthy)`.

- [ ] **Step 6: Stop the container (we don't need it running for the rest of M0)**

Run:
```bash
docker compose down
```

- [ ] **Step 7: Commit**

Run:
```bash
git add docker-compose.yml .env.example
git commit -m "feat: add local Postgres via Docker Compose"
```

---

## Task 7: Code-quality tooling

**Files:**
- Create: `biome.json`
- Create: `.pre-commit-config.yaml`

- [ ] **Step 1: Write `biome.json`**

Content:
```json
{
  "$schema": "https://biomejs.dev/schemas/1.9.4/schema.json",
  "vcs": { "enabled": true, "clientKind": "git", "useIgnoreFile": true },
  "files": {
    "ignore": [
      "**/node_modules/**",
      "**/.next/**",
      "**/dist/**",
      "**/.venv/**",
      "**/uv.lock",
      "**/pnpm-lock.yaml",
      "**/generated/**"
    ]
  },
  "organizeImports": { "enabled": true },
  "linter": {
    "enabled": true,
    "rules": {
      "recommended": true,
      "suspicious": { "noExplicitAny": "warn" },
      "style": {
        "useImportType": "error",
        "noNonNullAssertion": "warn"
      }
    }
  },
  "formatter": {
    "enabled": true,
    "indentStyle": "space",
    "indentWidth": 2,
    "lineWidth": 100
  },
  "javascript": {
    "formatter": {
      "quoteStyle": "double",
      "trailingCommas": "all",
      "semicolons": "always"
    }
  }
}
```

- [ ] **Step 2: Verify biome runs clean on the current tree**

Run from repo root:
```bash
pnpm lint
```
Expected: PASS with no errors. If biome flags anything, fix inline (likely import-ordering nits) and re-run.

- [ ] **Step 3: Verify typecheck runs clean**

Run from repo root:
```bash
pnpm typecheck
```
Expected: PASS with no errors.

- [ ] **Step 4: Verify Python tooling runs clean**

Run from `apps/api/`:
```bash
cd apps/api && uv run ruff check . && uv run ruff format --check . && uv run mypy src
```
Expected: All three commands pass. Fix any issues inline.

- [ ] **Step 5: Write `.pre-commit-config.yaml`**

Content:
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: [--maxkb=500]
      - id: check-merge-conflict
      - id: check-case-conflict

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.4
    hooks:
      - id: ruff
        args: [--fix]
        files: ^apps/api/
      - id: ruff-format
        files: ^apps/api/

  - repo: https://github.com/biomejs/pre-commit
    rev: v1.9.4
    hooks:
      - id: biome-check
        additional_dependencies: ["@biomejs/biome@1.9.4"]
```

- [ ] **Step 6: Install pre-commit hooks**

Run from repo root:
```bash
pre-commit install
```
Expected: `pre-commit installed at .git/hooks/pre-commit`.

- [ ] **Step 7: Run pre-commit on all files to verify clean baseline**

Run:
```bash
pre-commit run --all-files
```
Expected: all hooks pass. If any hooks modify files (e.g. end-of-file-fixer), re-stage and re-run until clean.

- [ ] **Step 8: Commit**

Run:
```bash
git add biome.json .pre-commit-config.yaml
git commit -m "chore: add biome + pre-commit code-quality tooling"
```

---

## Task 8: GitHub Actions CI on PRs

**Files:**
- Create: `.github/workflows/test.yml`

- [ ] **Step 1: Create the directory**

Run from repo root:
```bash
mkdir -p .github/workflows
```

- [ ] **Step 2: Write `.github/workflows/test.yml`**

Content:
```yaml
name: test

on:
  pull_request:
  push:
    branches: [main]

concurrency:
  group: test-${{ github.ref }}
  cancel-in-progress: true

jobs:
  web:
    name: Web — lint + typecheck + test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: pnpm/action-setup@v4
        with:
          version: 9.12.0

      - uses: actions/setup-node@v4
        with:
          node-version-file: ".nvmrc"
          cache: "pnpm"

      - name: Install workspace deps
        run: pnpm install --frozen-lockfile

      - name: Lint (biome)
        run: pnpm lint

      - name: Typecheck
        run: pnpm typecheck

      - name: Test
        run: pnpm test

  api:
    name: API — lint + typecheck + test
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: apps/api
    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v4
        with:
          enable-cache: true
          cache-dependency-glob: "apps/api/uv.lock"

      - name: Set up Python
        run: uv python install 3.12

      - name: Sync deps
        run: uv sync --frozen

      - name: Lint (ruff check)
        run: uv run ruff check .

      - name: Format check (ruff format --check)
        run: uv run ruff format --check .

      - name: Typecheck (mypy)
        run: uv run mypy src

      - name: Test (pytest)
        run: uv run pytest -v
```

- [ ] **Step 3: Commit**

Run:
```bash
git add .github/workflows/test.yml
git commit -m "ci: add lint + typecheck + test workflow for web and api"
```

- [ ] **Step 4: Push the branch to trigger CI**

Run:
```bash
git push -u origin main
```

- [ ] **Step 5: Watch CI**

Run:
```bash
gh run watch
```
Or open the Actions tab in the GitHub UI. Expected: both jobs (`web` and `api`) green within ~3 minutes.

- [ ] **Step 6: If CI fails, fix inline and recommit**

If any step fails: read the error, fix locally, run the equivalent command (`pnpm lint`, `pnpm typecheck`, `uv run ruff check .`, etc.), commit the fix, push, re-watch. Do NOT use `--no-verify` or skip pre-commit.

---

## Task 9: Verify the full demoable end-state

**Files:** None modified — this is a manual acceptance run.

- [ ] **Step 1: Verify `apps/web` dev server**

Run from repo root:
```bash
pnpm dev:web
```
Open `http://localhost:3000`. Expected: Gold Leaf Resume hello page renders with the gold-accented title. Stop with Ctrl+C.

- [ ] **Step 2: Verify `apps/api` dev server**

Run from repo root:
```bash
cd apps/api && uv run uvicorn src.main:app --reload --port 8000
```
In another terminal:
```bash
curl -s http://localhost:8000/healthz
```
Expected: `{"status":"ok"}`. Stop the server.

- [ ] **Step 3: Verify local Postgres**

Run:
```bash
docker compose up -d postgres
docker compose exec postgres psql -U goldleaf -d goldleaf -c "SELECT 1;"
docker compose down
```
Expected: `?column? \n--- \n   1 \n(1 row)`.

- [ ] **Step 4: Verify CI is green on `main`**

Run:
```bash
gh run list --branch main --limit 1
```
Expected: status `completed`, conclusion `success`.

---

## Task 10: Tag `sp1-m0` and update the SP1 spec status

**Files:**
- Modify: (back in `Brains_Resume_Skill` repo) `docs/specs/2026-05-18-sp1-gold-leaf-resume-platform-foundation.md` — update Status line to note M0 complete.

- [ ] **Step 1: Tag M0 in `gold-leaf-resume`**

Run from `gold-leaf-resume` repo root:
```bash
git tag -a sp1-m0 -m "SP1·M0 — Monorepo bootstrap complete. apps/web + apps/api scaffolded, local Postgres via docker compose, CI green."
git push --tags
```

- [ ] **Step 2: Update the SP1 spec status in the original repo**

Switch to the `Brains_Resume_Skill` repo. Edit `docs/specs/2026-05-18-sp1-gold-leaf-resume-platform-foundation.md`:

Find:
```markdown
**Status:** Approved — ready for plan writing
```

Replace with:
```markdown
**Status:** In implementation — SP1·M0 complete (2026-05-18 — `sp1-m0` tag in `gold-leaf-resume`); M1 (DB schema + Supabase setup) next.
```

- [ ] **Step 3: Commit the spec update in `Brains_Resume_Skill`**

Run from `c:/Brains_Resume_Skill`:
```bash
git add docs/specs/2026-05-18-sp1-gold-leaf-resume-platform-foundation.md
git commit -m "docs: mark SP1·M0 complete in spec status"
git push
```

---

## Self-review

**Spec coverage (against SP1 spec, only items M0 is responsible for):**

| Spec section | M0 coverage |
|---|---|
| §4.3 backend stack (FastAPI, Pydantic v2, uvicorn, structlog) | ✓ deps in `apps/api/pyproject.toml`; structlog imported but not exercised yet (M2) |
| §4.2 frontend stack (Next.js 15, TS strict, Tailwind, shadcn/ui) | ✓ Next.js + TS strict + Tailwind installed; shadcn/ui deferred to M3 when first components needed |
| §4.2 design tokens package | ✓ `packages/design-tokens` exists as placeholder (palette inline in `apps/web/tailwind.config.ts` for M0) |
| §4.2 shared-types package | ✓ `packages/shared-types` placeholder; populated when M2 generates OpenAPI types |
| §9.1 monorepo layout | ✓ matches spec exactly |
| §9.2 tooling (pnpm, uv, biome, ruff, mypy, vitest, pytest) | ✓ all installed and exercised |
| §9.3 CI test.yml | ✓ implemented |
| §9.4 environments — `local` | ✓ docker compose Postgres ready |
| §9.4 environments — `staging`, `production` | not in M0 — defer to M9 |
| §9.5 secrets — `.env.example` | ✓ top-level scaffold; per-app `.env.example` files added in M2 (API) and M3 (web) when env vars actually exist |
| All other §3 in-scope items (auth, DB, LLM abstraction, file storage, settings, etc.) | not in M0 — explicit milestone boundary |

**Placeholder scan:** searched the plan for "TBD", "TODO", "fill in", "implement later", "add appropriate" — none found. Every code block contains the actual code.

**Type consistency check:** the FastAPI app object is `app` in `src/main.py` and referenced as `from src.main import app` in `tests/test_health.py`. The Next.js `Home` component is exported as default from `app/page.tsx` and imported as `Home from "../app/page"` in the test. Tailwind colour names (`goldleaf-500`, `cream-50`, `ink-900`) used in `app/page.tsx` and `app/layout.tsx` all exist in `tailwind.config.ts`. Consistent.

**Pre-flight gotchas to flag on execution:**
- `gh repo create` requires the user to be authed to `shard-BRAINS` org with repo-create rights.
- `uv` version 0.4+ required (older versions don't support `[dependency-groups]`).
- pnpm 9.12 hashing is incompatible with pnpm 8 lockfiles — pristine `pnpm install` is fine since we're starting fresh.
- The Tailwind palette in `tailwind.config.ts` is M0's working copy; the canonical version moves to `packages/design-tokens` in M3.

---

**End of SP1·M0 plan.**
