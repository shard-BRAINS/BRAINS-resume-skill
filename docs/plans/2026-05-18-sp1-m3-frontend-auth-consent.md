# Gold Leaf Resume — SP1·M3: Frontend Auth + Consent Flows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the user-facing signup → verify → consent → authenticated-shell flow on `apps/web`. A new visitor can land on `/`, sign up with email/password OR Google OAuth OR magic link, verify their email, accept consent, and arrive at an empty `/app/dashboard` showing their Gold Leaf account name. Logged-in users who try `/app/*` without all mandatory consents are bounced to `/accept-consent`. Logged-out users hitting `/app/*` are bounced to `/login`. Settings, real dashboard content, and per-vertical pages are NOT in M3 — they ship in M6 (Settings), SP2-SP5 (verticals).

**Architecture:** Next.js 15 App Router with `@supabase/ssr` for cookie-based session management across server + client. Two-layer consent enforcement: Next.js middleware checks session presence (fast path), and a server-side hook in `/app/*` layouts checks consent status via `GET /v1/me` (authoritative). Forms use react-hook-form + zod. shadcn/ui provides accessible primitives. The typed API client comes from `@goldleafresume/shared-types` (M2's OpenAPI output) wrapped with `openapi-fetch` for type-safe `GET/POST` calls.

**Tech Stack additions on top of M2:** `@supabase/ssr` (cookie-aware auth), `@supabase/supabase-js` (client core), `@tanstack/react-query` (server state for API calls), `openapi-fetch` (typed fetch using shared-types), `react-hook-form` + `zod` + `@hookform/resolvers` (forms), `lucide-react` (icon set for shadcn). For shadcn/ui: 6 components installed individually (button, input, label, card, alert, separator).

**Predecessor:** SP1·M2 (Backend auth + consent middleware) — tag `sp1-m2` on `gold-leaf-resume`.
**Spec:** [docs/specs/2026-05-18-sp1-gold-leaf-resume-platform-foundation.md](../specs/2026-05-18-sp1-gold-leaf-resume-platform-foundation.md) §4.2 (frontend stack), §4.7 (auth + consent flow), §4.2 IA / sidebar nav.

**Demoable end state:**
1. `pnpm db:start && pnpm dev:web` (with `apps/api` running too). Open `http://localhost:3000/` → marketing-light landing with "Sign in" + "Sign up" CTAs.
2. Click Sign up → email/password form. Submit with a new email → Supabase sends verification email (caught by Mailpit at `http://localhost:54324`). Click the link → land at `/accept-consent`.
3. Toggle the three mandatory consents (TOS, Privacy, Sensitive Data AU) + optionally marketing → submit. Backend records consent. Frontend redirects to `/app/dashboard`.
4. `/app/dashboard` (and all other `/app/*` pages) render the shell layout: top bar with Gold Leaf branding + account display name + logout, sidebar with journey-stage nav (1·Apply, 2·Build, 3·Track), main pane with "Coming soon — SP2 will populate this" per page.
5. Open a private window → visit `/app/dashboard` directly → redirected to `/login`.
6. Sign in with the verified user → land back at `/app/dashboard`.
7. Open a fresh signup that doesn't accept consent → visit `/app/dashboard` → redirected to `/accept-consent`.
8. Forgot password flow: from `/login`, click "Forgot password?" → submit email → receive reset email via Mailpit → click link → land at `/reset-password?...` → set new password → land at `/login`.
9. Magic link flow: from `/login`, click "Email me a sign-in link" → submit email → receive link via Mailpit → click → bypass password → land at `/accept-consent` (if first time) or `/app/dashboard`.
10. Google OAuth: from `/login`, click "Continue with Google" → consent screen → callback → `/app/dashboard` (if consents already given) or `/accept-consent` (if first time).
11. All `/legal/{terms,privacy,cookies}` pages render placeholder content (real copy lands in SP7).
12. Vitest + Playwright tests pass; CI green.
13. Tag `sp1-m3` exists on `main`, reached via squash-merge from feature branch `m3-frontend-auth-consent`.

---

## Open prerequisites (resolve before Task 5+)

- [ ] **Google OAuth credentials** (for Task 5b).
  1. Visit https://console.cloud.google.com/apis/credentials.
  2. Create a new OAuth 2.0 Client ID, type **Web application**.
  3. Add authorized redirect URIs: `http://127.0.0.1:54321/auth/v1/callback` (for local Supabase) and (later) `https://<your-supabase-staging>.supabase.co/auth/v1/callback`.
  4. Copy the Client ID + Client Secret.
  5. In `c:/gold-leaf-resume/infra/supabase/config.toml`, under `[auth.external.google]`, set `enabled = true`, paste the credentials.
  6. Restart Supabase: `pnpm db:stop && pnpm db:start`.
  7. If you can't / don't want to set up Google OAuth now, mark Task 5b as deferred — email/password + magic link still cover the demo.

- [ ] **Mailpit for local email** is already running (Supabase CLI brings it up at `http://127.0.0.1:54324`). Verification/reset emails land there. Open it in a browser during testing.

- [ ] **Feature branch workflow.** All M3 work lives on `m3-frontend-auth-consent`. PR squash-merge into `main` at the end.

- [ ] **Supabase URL config for password reset + magic link** — set in `infra/supabase/config.toml`:
  ```toml
  [auth]
  site_url = "http://127.0.0.1:3000"
  additional_redirect_urls = ["http://127.0.0.1:3000/**"]
  ```
  Otherwise reset links + magic links land at the wrong place. Task 2 will handle this.

---

## File Structure

```
gold-leaf-resume/                            (existing)
├── packages/
│   └── design-tokens/                       MODIFIED — actually populated now (M3 owns this)
│       ├── src/index.ts                     re-exports tokens
│       └── src/tokens.ts                    NEW — Gold Leaf palette + semantic tokens
│
├── apps/web/                                most of the M3 work here
│   ├── package.json                         +deps (Supabase, react-query, openapi-fetch, RHF, zod, lucide)
│   ├── tailwind.config.ts                   MODIFIED — import tokens from packages/design-tokens
│   ├── components.json                      NEW — shadcn/ui config
│   ├── .env.local.example                   NEW — public Supabase URL + anon key + API base URL
│   ├── middleware.ts                        NEW — Next.js middleware (auth fast-path on /app/*)
│   ├── app/
│   │   ├── page.tsx                         MODIFIED — landing page polish
│   │   ├── layout.tsx                       MODIFIED — react-query provider, font setup
│   │   ├── globals.css                      MODIFIED — shadcn CSS variables
│   │   ├── (auth)/                          route group, no URL segment
│   │   │   ├── layout.tsx                   NEW — centered card layout for auth pages
│   │   │   ├── signup/page.tsx              NEW — email/password + OAuth/magic-link buttons
│   │   │   ├── login/page.tsx               NEW — email/password + OAuth/magic-link buttons + forgot-password
│   │   │   ├── verify/page.tsx              NEW — handles Supabase email-verify callback
│   │   │   ├── reset-password/page.tsx      NEW — set new password form
│   │   │   └── forgot-password/page.tsx     NEW — request reset email form
│   │   ├── accept-consent/page.tsx          NEW — four toggles + submit
│   │   ├── legal/
│   │   │   ├── terms/page.tsx               NEW — stub content
│   │   │   ├── privacy/page.tsx             NEW — stub content
│   │   │   └── cookies/page.tsx             NEW — stub content
│   │   ├── api/
│   │   │   └── auth/
│   │   │       └── callback/route.ts        NEW — OAuth + magic-link callback handler
│   │   └── app/                             AUTHENTICATED shell
│   │       ├── layout.tsx                   NEW — sidebar + top bar; checks session + consent
│   │       ├── dashboard/page.tsx           NEW — placeholder
│   │       ├── resumes/page.tsx             NEW — placeholder
│   │       ├── jds/page.tsx                 NEW — placeholder
│   │       ├── cover-letters/page.tsx       NEW — placeholder
│   │       ├── applications/page.tsx        NEW — placeholder
│   │       ├── analytics/page.tsx           NEW — placeholder
│   │       ├── pacing/page.tsx              NEW — placeholder
│   │       └── settings/page.tsx            NEW — placeholder (real Settings in M6)
│   ├── components/
│   │   ├── ui/                              shadcn/ui generated components
│   │   │   ├── button.tsx
│   │   │   ├── input.tsx
│   │   │   ├── label.tsx
│   │   │   ├── card.tsx
│   │   │   ├── alert.tsx
│   │   │   └── separator.tsx
│   │   ├── auth/
│   │   │   ├── email-password-form.tsx      NEW — shared between signup + login
│   │   │   ├── oauth-buttons.tsx            NEW — Google OAuth button (extensible)
│   │   │   ├── magic-link-form.tsx          NEW
│   │   │   └── logout-button.tsx            NEW
│   │   ├── app/
│   │   │   ├── shell.tsx                    NEW — authenticated shell wrapper
│   │   │   ├── sidebar.tsx                  NEW — journey-stage nav
│   │   │   └── top-bar.tsx                  NEW — branding + account display + logout
│   │   ├── consent/
│   │   │   └── consent-form.tsx             NEW — four toggles
│   │   └── providers.tsx                    NEW — react-query provider wrapper
│   ├── lib/
│   │   ├── supabase/
│   │   │   ├── client.ts                    NEW — browser client (singleton)
│   │   │   ├── server.ts                    NEW — server-side client (cookie-aware)
│   │   │   └── middleware.ts                NEW — refreshSession helper for middleware.ts
│   │   ├── api/
│   │   │   ├── client.ts                    NEW — openapi-fetch instance bound to API base URL
│   │   │   └── hooks.ts                     NEW — react-query wrappers (useMe, useGrantConsent)
│   │   ├── consent.ts                       NEW — REQUIRED_CONSENT_KINDS const (mirrors backend)
│   │   └── env.ts                           NEW — typed access to NEXT_PUBLIC_* env vars
│   └── tests/
│       ├── home.test.tsx                    (existing, unchanged)
│       ├── components/
│       │   ├── email-password-form.test.tsx NEW
│       │   └── consent-form.test.tsx        NEW
│       └── e2e/                             Playwright (only if configured)
│           └── auth-flow.spec.ts            NEW (deferred to Task 11 — optional)
│
├── infra/supabase/config.toml               MODIFIED — site_url, redirect URLs, Google OAuth section
│
└── .github/workflows/test.yml               MODIFIED — web job runs new tests
```

**Why this layout:**
- Route groups `(auth)` keep auth pages on a centered-card layout without affecting the URL.
- `lib/supabase/{client,server,middleware}.ts` is the canonical `@supabase/ssr` pattern — three clients, one per execution context.
- `lib/api/client.ts` is the single typed-fetch instance; route handlers + RQ hooks both consume it.
- shadcn components in `components/ui/` are owned code (not a dep), per shadcn's design.
- Tests stay in `apps/web/tests/`; Vitest config already wired in M0.

---

## Task 1: Branch + design tokens unification + shadcn/ui base

**Files:**
- Create: `packages/design-tokens/src/tokens.ts`
- Modify: `packages/design-tokens/src/index.ts`
- Modify: `apps/web/tailwind.config.ts`
- Modify: `apps/web/app/globals.css`
- Create: `apps/web/components.json`
- Create: `apps/web/components/ui/{button,input,label,card,alert,separator}.tsx` (via shadcn CLI)
- Modify: `apps/web/package.json`

- [ ] **Step 1: Branch**
```bash
cd c:/gold-leaf-resume && git checkout main && git pull && git checkout -b m3-frontend-auth-consent
```

- [ ] **Step 2: Populate `packages/design-tokens/src/tokens.ts`**

Content:
```typescript
/**
 * Gold Leaf Resume — design tokens.
 *
 * Single source of truth for color/spacing/typography across the web app.
 * Tailwind imports this via tailwind.config.ts; CSS variables in globals.css
 * mirror the semantic tokens for shadcn/ui compatibility.
 */

export const colors = {
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
  brains: {
    blue: "#1e40af",
  },
} as const;
```

- [ ] **Step 3: Update `packages/design-tokens/src/index.ts`**
```typescript
// Gold Leaf Resume — design tokens.
// Populated in SP1·M3.

export { colors } from "./tokens";
```

- [ ] **Step 4: Update `apps/web/tailwind.config.ts` to import tokens**

```typescript
import { colors as tokens } from "@goldleafresume/design-tokens";
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Brand palette
        goldleaf: tokens.goldleaf,
        cream: tokens.cream,
        ink: tokens.ink,
        brains: tokens.brains,

        // shadcn semantic tokens (mapped to CSS vars in globals.css)
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [],
};

export default config;
```

- [ ] **Step 5: Update `apps/web/app/globals.css` with shadcn CSS variables**

Content:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 44 80% 98%;          /* cream-50 */
    --foreground: 30 16% 8%;            /* ink-900 */
    --card: 0 0% 100%;
    --card-foreground: 30 16% 8%;
    --popover: 0 0% 100%;
    --popover-foreground: 30 16% 8%;
    --primary: 45 80% 42%;              /* goldleaf-500 */
    --primary-foreground: 44 80% 98%;
    --secondary: 44 60% 92%;
    --secondary-foreground: 30 16% 8%;
    --muted: 44 30% 92%;
    --muted-foreground: 30 8% 40%;
    --accent: 44 60% 88%;
    --accent-foreground: 30 16% 8%;
    --destructive: 0 70% 50%;
    --destructive-foreground: 0 0% 100%;
    --border: 44 25% 88%;
    --input: 44 25% 88%;
    --ring: 45 80% 42%;
    --radius: 0.5rem;
  }

  .dark {
    --background: 30 16% 5%;            /* ink-950 */
    --foreground: 44 60% 96%;
    --card: 30 16% 8%;
    --card-foreground: 44 60% 96%;
    --popover: 30 16% 8%;
    --popover-foreground: 44 60% 96%;
    --primary: 45 80% 50%;
    --primary-foreground: 30 16% 8%;
    --secondary: 30 12% 14%;
    --secondary-foreground: 44 60% 96%;
    --muted: 30 12% 14%;
    --muted-foreground: 44 12% 60%;
    --accent: 30 12% 16%;
    --accent-foreground: 44 60% 96%;
    --destructive: 0 60% 45%;
    --destructive-foreground: 0 0% 100%;
    --border: 30 12% 18%;
    --input: 30 12% 18%;
    --ring: 45 80% 50%;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
    font-feature-settings: "rlig" 1, "calt" 1;
  }
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

- [ ] **Step 6: Add shadcn/ui deps to `apps/web/package.json`**

In `apps/web/package.json`, append to `dependencies`:
```json
    "@radix-ui/react-label": "2.1.1",
    "@radix-ui/react-separator": "1.1.1",
    "@radix-ui/react-slot": "1.1.1",
    "class-variance-authority": "0.7.1",
    "clsx": "2.1.1",
    "lucide-react": "0.469.0",
    "tailwind-merge": "2.6.0",
    "tailwindcss-animate": "1.0.7"
```

And to `devDependencies`:
```json
    "@goldleafresume/design-tokens": "workspace:*"
```

- [ ] **Step 7: Create `apps/web/components.json`** (shadcn config)
```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "default",
  "rsc": true,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.ts",
    "css": "app/globals.css",
    "baseColor": "neutral",
    "cssVariables": true,
    "prefix": ""
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  },
  "iconLibrary": "lucide"
}
```

- [ ] **Step 8: Install workspace deps + add tailwindcss-animate to config**

```bash
cd c:/gold-leaf-resume && pnpm install
```

Then update `apps/web/tailwind.config.ts` plugins array:
```typescript
import tailwindcssAnimate from "tailwindcss-animate";
// ... in the config object, replace plugins: []:
  plugins: [tailwindcssAnimate],
```

- [ ] **Step 9: Create `apps/web/lib/utils.ts`** (shadcn's standard helper)

```typescript
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 10: Create `apps/web/components/ui/button.tsx`**

Standard shadcn button. Content:
```typescript
import { Slot } from "@radix-ui/react-slot";
import { type VariantProps, cva } from "class-variance-authority";
import * as React from "react";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
```

- [ ] **Step 11: Create `apps/web/components/ui/input.tsx`**

```typescript
import * as React from "react";

import { cn } from "@/lib/utils";

const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
          className,
        )}
        ref={ref}
        {...props}
      />
    );
  },
);
Input.displayName = "Input";

export { Input };
```

- [ ] **Step 12: Create `apps/web/components/ui/label.tsx`**

```typescript
"use client";

import * as LabelPrimitive from "@radix-ui/react-label";
import { type VariantProps, cva } from "class-variance-authority";
import * as React from "react";

import { cn } from "@/lib/utils";

const labelVariants = cva(
  "text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70",
);

const Label = React.forwardRef<
  React.ElementRef<typeof LabelPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof LabelPrimitive.Root> & VariantProps<typeof labelVariants>
>(({ className, ...props }, ref) => (
  <LabelPrimitive.Root ref={ref} className={cn(labelVariants(), className)} {...props} />
));
Label.displayName = LabelPrimitive.Root.displayName;

export { Label };
```

- [ ] **Step 13: Create `apps/web/components/ui/card.tsx`**

```typescript
import * as React from "react";

import { cn } from "@/lib/utils";

const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("rounded-lg border bg-card text-card-foreground shadow-sm", className)}
      {...props}
    />
  ),
);
Card.displayName = "Card";

const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex flex-col space-y-1.5 p-6", className)} {...props} />
  ),
);
CardHeader.displayName = "CardHeader";

const CardTitle = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("text-2xl font-semibold leading-none tracking-tight", className)}
      {...props}
    />
  ),
);
CardTitle.displayName = "CardTitle";

const CardDescription = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("text-sm text-muted-foreground", className)} {...props} />
  ),
);
CardDescription.displayName = "CardDescription";

const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />
  ),
);
CardContent.displayName = "CardContent";

const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex items-center p-6 pt-0", className)} {...props} />
  ),
);
CardFooter.displayName = "CardFooter";

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent };
```

- [ ] **Step 14: Create `apps/web/components/ui/alert.tsx`**

```typescript
import { type VariantProps, cva } from "class-variance-authority";
import * as React from "react";

import { cn } from "@/lib/utils";

const alertVariants = cva(
  "relative w-full rounded-lg border p-4 [&>svg~*]:pl-7 [&>svg+div]:translate-y-[-3px] [&>svg]:absolute [&>svg]:left-4 [&>svg]:top-4 [&>svg]:text-foreground",
  {
    variants: {
      variant: {
        default: "bg-background text-foreground",
        destructive:
          "border-destructive/50 text-destructive dark:border-destructive [&>svg]:text-destructive",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

const Alert = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & VariantProps<typeof alertVariants>
>(({ className, variant, ...props }, ref) => (
  <div ref={ref} role="alert" className={cn(alertVariants({ variant }), className)} {...props} />
));
Alert.displayName = "Alert";

const AlertTitle = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h5 ref={ref} className={cn("mb-1 font-medium leading-none tracking-tight", className)} {...props} />
  ),
);
AlertTitle.displayName = "AlertTitle";

const AlertDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("text-sm [&_p]:leading-relaxed", className)} {...props} />
));
AlertDescription.displayName = "AlertDescription";

export { Alert, AlertTitle, AlertDescription };
```

- [ ] **Step 15: Create `apps/web/components/ui/separator.tsx`**

```typescript
"use client";

import * as SeparatorPrimitive from "@radix-ui/react-separator";
import * as React from "react";

import { cn } from "@/lib/utils";

const Separator = React.forwardRef<
  React.ElementRef<typeof SeparatorPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof SeparatorPrimitive.Root>
>(({ className, orientation = "horizontal", decorative = true, ...props }, ref) => (
  <SeparatorPrimitive.Root
    ref={ref}
    decorative={decorative}
    orientation={orientation}
    className={cn(
      "shrink-0 bg-border",
      orientation === "horizontal" ? "h-[1px] w-full" : "h-full w-[1px]",
      className,
    )}
    {...props}
  />
));
Separator.displayName = SeparatorPrimitive.Root.displayName;

export { Separator };
```

- [ ] **Step 16: Update `apps/web/tsconfig.json` path aliases**

Confirm `paths` includes `@/*`. If not, edit `compilerOptions.paths`:
```json
"paths": { "@/*": ["./*"] }
```
(Already present from M0 — verify.)

- [ ] **Step 17: Verify build + typecheck**

```bash
cd c:/gold-leaf-resume && pnpm install && pnpm typecheck
```
Expected: no errors. The new tokens import + UI components should typecheck cleanly.

```bash
cd c:/gold-leaf-resume && pnpm --filter web test
```
Expected: existing `home.test.tsx` still passes (2 tests).

- [ ] **Step 18: Commit**

```bash
cd c:/gold-leaf-resume && git add packages/design-tokens/ apps/web/ pnpm-lock.yaml
git commit -m "feat(web): populate design-tokens + add 6 shadcn/ui base components"
```

---

## Task 2: Supabase JS client setup (browser + server + middleware) + env

**Files:**
- Modify: `apps/web/package.json` (add @supabase/ssr + supabase-js)
- Create: `apps/web/lib/env.ts`
- Create: `apps/web/lib/supabase/client.ts`
- Create: `apps/web/lib/supabase/server.ts`
- Create: `apps/web/lib/supabase/middleware.ts`
- Create: `apps/web/.env.local.example`
- Create: `apps/web/.env.local` (local-only, gitignored)
- Modify: `infra/supabase/config.toml` (site_url + redirect URLs)

- [ ] **Step 1: Add Supabase deps**

In `apps/web/package.json` `dependencies`:
```json
    "@supabase/ssr": "0.5.2",
    "@supabase/supabase-js": "2.47.10"
```

Then:
```bash
cd c:/gold-leaf-resume && pnpm install
```

- [ ] **Step 2: Create `apps/web/lib/env.ts`**

```typescript
/**
 * Typed access to public environment variables.
 * Throws at module load if any required var is missing.
 */

function required(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required env var: ${name}`);
  }
  return value;
}

export const env = {
  NEXT_PUBLIC_SUPABASE_URL: required("NEXT_PUBLIC_SUPABASE_URL"),
  NEXT_PUBLIC_SUPABASE_ANON_KEY: required("NEXT_PUBLIC_SUPABASE_ANON_KEY"),
  NEXT_PUBLIC_API_URL: required("NEXT_PUBLIC_API_URL"),
} as const;
```

- [ ] **Step 3: Create `apps/web/lib/supabase/client.ts`** (browser singleton)

```typescript
"use client";

import { createBrowserClient } from "@supabase/ssr";

import { env } from "@/lib/env";

let _client: ReturnType<typeof createBrowserClient> | null = null;

/** Browser-only Supabase client. Singleton — call from "use client" components. */
export function getSupabaseBrowserClient() {
  if (!_client) {
    _client = createBrowserClient(env.NEXT_PUBLIC_SUPABASE_URL, env.NEXT_PUBLIC_SUPABASE_ANON_KEY);
  }
  return _client;
}
```

- [ ] **Step 4: Create `apps/web/lib/supabase/server.ts`** (server-side, cookie-aware)

```typescript
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

import { env } from "@/lib/env";

/**
 * Server-side Supabase client for Server Components, Route Handlers,
 * and Server Actions. Reads/writes cookies via Next's cookie store.
 */
export async function getSupabaseServerClient() {
  const cookieStore = await cookies();
  return createServerClient(env.NEXT_PUBLIC_SUPABASE_URL, env.NEXT_PUBLIC_SUPABASE_ANON_KEY, {
    cookies: {
      getAll() {
        return cookieStore.getAll();
      },
      setAll(cookiesToSet) {
        try {
          for (const { name, value, options } of cookiesToSet) {
            cookieStore.set(name, value, options);
          }
        } catch {
          // Called from a Server Component — cookies are read-only there.
          // The session will be refreshed by middleware before reaching server components.
        }
      },
    },
  });
}
```

- [ ] **Step 5: Create `apps/web/lib/supabase/middleware.ts`** (used by `middleware.ts`)

```typescript
import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

import { env } from "@/lib/env";

/**
 * Refresh the Supabase session on every request.
 * Called from Next.js middleware (apps/web/middleware.ts).
 *
 * Returns the response to forward — DO NOT modify cookies on it after this
 * function returns, otherwise the refreshed session can be lost.
 */
export async function updateSupabaseSession(request: NextRequest) {
  let response = NextResponse.next({
    request,
  });

  const supabase = createServerClient(
    env.NEXT_PUBLIC_SUPABASE_URL,
    env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          for (const { name, value } of cookiesToSet) {
            request.cookies.set(name, value);
          }
          response = NextResponse.next({ request });
          for (const { name, value, options } of cookiesToSet) {
            response.cookies.set(name, value, options);
          }
        },
      },
    },
  );

  // IMPORTANT: refreshes the access token if expired. Must call getUser(), not getSession().
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return { response, user, supabase };
}
```

- [ ] **Step 6: Create `apps/web/.env.local.example`**

```bash
# Gold Leaf Resume — Web local environment
# Copy to apps/web/.env.local (gitignored). All NEXT_PUBLIC_* are exposed to the browser.

NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
NEXT_PUBLIC_SUPABASE_ANON_KEY=<paste Publishable key from `supabase status` — same value as apps/api/.env SUPABASE_ANON_KEY>
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

- [ ] **Step 7: Create `apps/web/.env.local`** (local-only, gitignored)

Get the Publishable key:
```bash
cd c:/gold-leaf-resume/infra/supabase && supabase status | grep -i "publishable" | awk '{print $NF}'
```

Paste the value:
```bash
NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
NEXT_PUBLIC_SUPABASE_ANON_KEY=<paste>
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

Confirm `.env.local` does NOT appear in `git status` (already covered by `.gitignore`'s `.env.*.local` rule).

- [ ] **Step 8: Modify `infra/supabase/config.toml`**

Find the `[auth]` section and update:
```toml
[auth]
enable_signup = true
site_url = "http://127.0.0.1:3000"
additional_redirect_urls = ["http://127.0.0.1:3000/**"]
```

If `site_url` already exists, change the value; same for `additional_redirect_urls`.

- [ ] **Step 9: Restart Supabase to pick up config changes**

```bash
cd c:/gold-leaf-resume && pnpm db:stop && pnpm db:start
```

After restart, verify:
```bash
cd c:/gold-leaf-resume && pnpm db:status | head -10
```

- [ ] **Step 10: Verify imports compile**

```bash
cd c:/gold-leaf-resume && pnpm typecheck
```
Expected: clean.

- [ ] **Step 11: Commit**

```bash
cd c:/gold-leaf-resume && git add apps/web/ infra/supabase/config.toml pnpm-lock.yaml
git commit -m "feat(web): Supabase SSR client (browser/server/middleware) + env scaffolding"
```

---

## Task 3: Typed API client + react-query setup

**Files:**
- Modify: `apps/web/package.json`
- Create: `apps/web/lib/api/client.ts`
- Create: `apps/web/lib/api/hooks.ts`
- Create: `apps/web/lib/consent.ts`
- Create: `apps/web/components/providers.tsx`
- Modify: `apps/web/app/layout.tsx`

- [ ] **Step 1: Add deps**

In `apps/web/package.json` `dependencies`:
```json
    "@tanstack/react-query": "5.62.11",
    "openapi-fetch": "0.13.1",
    "react-hook-form": "7.54.2",
    "@hookform/resolvers": "3.9.1",
    "zod": "3.24.1"
```

```bash
cd c:/gold-leaf-resume && pnpm install
```

- [ ] **Step 2: Create `apps/web/lib/consent.ts`**

```typescript
/** Mirrors apps/api/src/schemas/me.py REQUIRED_CONSENT_KINDS. Keep in sync. */
export const REQUIRED_CONSENT_KINDS = ["tos", "privacy_policy", "sensitive_data_au"] as const;

/** All consent kinds the backend recognizes. */
export const ALL_CONSENT_KINDS = [
  "tos",
  "privacy_policy",
  "sensitive_data_au",
  "marketing_email",
] as const;

export type ConsentKind = (typeof ALL_CONSENT_KINDS)[number];
```

- [ ] **Step 3: Create `apps/web/lib/api/client.ts`**

```typescript
"use client";

import createClient from "openapi-fetch";

import { env } from "@/lib/env";
import { getSupabaseBrowserClient } from "@/lib/supabase/client";
import type { paths } from "@goldleafresume/shared-types";

/**
 * Typed fetch instance bound to the FastAPI backend.
 *
 * Each call automatically adds an Authorization Bearer header with the current
 * Supabase access token. If the token is missing, the request is sent without
 * Authorization — the backend returns 401, which RQ surfaces to the caller.
 */
function buildClient() {
  return createClient<paths>({
    baseUrl: env.NEXT_PUBLIC_API_URL,
    fetch: async (input, init) => {
      const supabase = getSupabaseBrowserClient();
      const { data: { session } } = await supabase.auth.getSession();
      const headers = new Headers(init?.headers);
      if (session?.access_token) {
        headers.set("Authorization", `Bearer ${session.access_token}`);
      }
      return fetch(input, { ...init, headers });
    },
  });
}

let _apiClient: ReturnType<typeof buildClient> | null = null;

export function getApiClient() {
  if (!_apiClient) {
    _apiClient = buildClient();
  }
  return _apiClient;
}
```

- [ ] **Step 4: Create `apps/web/lib/api/hooks.ts`**

```typescript
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getApiClient } from "@/lib/api/client";
import type { ConsentKind } from "@/lib/consent";

const ME_QUERY_KEY = ["me"] as const;

/** Fetch /v1/me — identity, account, consent status. */
export function useMe() {
  return useQuery({
    queryKey: ME_QUERY_KEY,
    queryFn: async () => {
      const client = getApiClient();
      const { data, error } = await client.GET("/v1/me");
      if (error) throw new Error(JSON.stringify(error));
      return data!;
    },
    retry: (failureCount, err) => {
      // Don't retry 401s — they mean we're not authed yet.
      const msg = err instanceof Error ? err.message : "";
      if (msg.includes("unauthenticated")) return false;
      return failureCount < 2;
    },
  });
}

/** POST /v1/me/consent — record one consent decision. */
export function useGrantConsent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: { kind: ConsentKind; version: string; granted: boolean }) => {
      const client = getApiClient();
      const { data, error } = await client.POST("/v1/me/consent", { body });
      if (error) throw new Error(JSON.stringify(error));
      return data!;
    },
    onSuccess: () => {
      // Refetch /v1/me so consent_status reflects the new state.
      queryClient.invalidateQueries({ queryKey: ME_QUERY_KEY });
    },
  });
}
```

- [ ] **Step 5: Create `apps/web/components/providers.tsx`**

```typescript
"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
```

- [ ] **Step 6: Wire Providers into root layout**

Open `apps/web/app/layout.tsx` and update:
```typescript
import type { Metadata } from "next";

import { Providers } from "@/components/providers";

import "./globals.css";

export const metadata: Metadata = {
  title: "Gold Leaf Resume",
  description:
    "ND-aware resume and job-application management. A shard product under BRAINS Incubator.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

(The `bg-cream-50 text-ink-900 dark:bg-ink-950 dark:text-cream-50` classes are now applied via `body` rules in globals.css — no need to put them on `<html>`.)

- [ ] **Step 7: Verify**

```bash
cd c:/gold-leaf-resume && pnpm typecheck && pnpm --filter web test
```
Expected: clean + existing 2 tests pass.

- [ ] **Step 8: Commit**

```bash
cd c:/gold-leaf-resume && git add apps/web/ pnpm-lock.yaml
git commit -m "feat(web): typed API client (openapi-fetch) + react-query provider + useMe/useGrantConsent hooks"
```

---

## Task 4: Email/password signup + login pages

**Files:**
- Create: `apps/web/app/(auth)/layout.tsx`
- Create: `apps/web/app/(auth)/signup/page.tsx`
- Create: `apps/web/app/(auth)/login/page.tsx`
- Create: `apps/web/components/auth/email-password-form.tsx`
- Create: `apps/web/app/api/auth/callback/route.ts`

- [ ] **Step 1: Create `apps/web/app/(auth)/layout.tsx`**

```typescript
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-md">{children}</div>
    </div>
  );
}
```

- [ ] **Step 2: Create `apps/web/components/auth/email-password-form.tsx`**

```typescript
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getSupabaseBrowserClient } from "@/lib/supabase/client";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(8, "At least 8 characters"),
});

type FormValues = z.infer<typeof schema>;

type Props = {
  mode: "signup" | "login";
};

export function EmailPasswordForm({ mode }: Props) {
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);
  const [showVerifyHint, setShowVerifyHint] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    const supabase = getSupabaseBrowserClient();

    if (mode === "signup") {
      const { error } = await supabase.auth.signUp({
        email: values.email,
        password: values.password,
        options: { emailRedirectTo: `${window.location.origin}/api/auth/callback` },
      });
      if (error) {
        setServerError(error.message);
        return;
      }
      setShowVerifyHint(true);
    } else {
      const { error } = await supabase.auth.signInWithPassword({
        email: values.email,
        password: values.password,
      });
      if (error) {
        setServerError(error.message);
        return;
      }
      // Server middleware will route to /accept-consent or /app/dashboard based on consent state.
      router.push("/app/dashboard");
      router.refresh();
    }
  };

  if (showVerifyHint) {
    return (
      <Alert>
        <AlertDescription>
          Check your email for a verification link. (Local dev: open Mailpit at{" "}
          <a href="http://127.0.0.1:54324" className="underline" target="_blank" rel="noreferrer">
            127.0.0.1:54324
          </a>
          .)
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="email">Email</Label>
        <Input id="email" type="email" autoComplete="email" {...register("email")} />
        {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
      </div>
      <div className="space-y-2">
        <Label htmlFor="password">Password</Label>
        <Input
          id="password"
          type="password"
          autoComplete={mode === "signup" ? "new-password" : "current-password"}
          {...register("password")}
        />
        {errors.password && <p className="text-xs text-destructive">{errors.password.message}</p>}
      </div>
      {serverError && (
        <Alert variant="destructive">
          <AlertDescription>{serverError}</AlertDescription>
        </Alert>
      )}
      <Button type="submit" disabled={isSubmitting} className="w-full">
        {isSubmitting ? "Working..." : mode === "signup" ? "Create account" : "Sign in"}
      </Button>
    </form>
  );
}
```

- [ ] **Step 3: Create `apps/web/app/(auth)/signup/page.tsx`**

```typescript
import Link from "next/link";

import { EmailPasswordForm } from "@/components/auth/email-password-form";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function SignupPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Create your account</CardTitle>
        <CardDescription>
          ND-aware resume + application management. By signing up you agree to our terms once
          consent is granted on the next screen.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <EmailPasswordForm mode="signup" />
        <p className="text-center text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link href="/login" className="text-primary underline-offset-4 hover:underline">
            Sign in
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 4: Create `apps/web/app/(auth)/login/page.tsx`**

```typescript
import Link from "next/link";

import { EmailPasswordForm } from "@/components/auth/email-password-form";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function LoginPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Sign in</CardTitle>
        <CardDescription>Welcome back.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <EmailPasswordForm mode="login" />
        <div className="flex items-center justify-between text-sm">
          <Link href="/forgot-password" className="text-muted-foreground hover:underline">
            Forgot password?
          </Link>
          <Link href="/signup" className="text-primary underline-offset-4 hover:underline">
            Create account
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 5: Create `apps/web/app/api/auth/callback/route.ts`**

```typescript
import { NextResponse } from "next/server";

import { getSupabaseServerClient } from "@/lib/supabase/server";

/**
 * OAuth + magic-link + email-verification callback.
 *
 * Supabase redirects here with `?code=...` after the user clicks an emailed link
 * or completes an OAuth flow. We exchange the code for a session (set as cookies)
 * and then redirect to the appropriate landing page.
 */
export async function GET(request: Request) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const next = url.searchParams.get("next") ?? "/accept-consent";

  if (code) {
    const supabase = await getSupabaseServerClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (error) {
      return NextResponse.redirect(`${url.origin}/login?error=${encodeURIComponent(error.message)}`);
    }
  }

  return NextResponse.redirect(`${url.origin}${next}`);
}
```

- [ ] **Step 6: Manual smoke test (optional but recommended)**

Start everything:
```bash
# Terminal 1
cd c:/gold-leaf-resume && pnpm db:start

# Terminal 2
cd c:/gold-leaf-resume/apps/api && uv run --env-file=.env uvicorn src.main:app --port 8000 --reload

# Terminal 3
cd c:/gold-leaf-resume && pnpm dev:web
```

Visit `http://localhost:3000/signup`. Fill in a real-looking email + 8+ char password. Submit. Verify message shows up. Open Mailpit at `http://127.0.0.1:54324`. Click the verification link. Should redirect to `/accept-consent` (which doesn't exist yet — page errors are fine, Task 7 builds it).

- [ ] **Step 7: Run tests**

```bash
cd c:/gold-leaf-resume && pnpm --filter web test
```
Expected: existing 2 tests still pass (no new tests yet — those come in Task 11).

- [ ] **Step 8: Commit**

```bash
cd c:/gold-leaf-resume && git add apps/web/
git commit -m "feat(web): /signup + /login email-password forms + OAuth callback route"
```

---

## Task 5: Google OAuth + magic link buttons

**Files:**
- Create: `apps/web/components/auth/oauth-buttons.tsx`
- Create: `apps/web/components/auth/magic-link-form.tsx`
- Modify: `apps/web/app/(auth)/signup/page.tsx`
- Modify: `apps/web/app/(auth)/login/page.tsx`
- Modify: `infra/supabase/config.toml` (enable Google OAuth — IF prereqs satisfied)

- [ ] **Step 1: Create `apps/web/components/auth/oauth-buttons.tsx`**

```typescript
"use client";

import { Button } from "@/components/ui/button";
import { getSupabaseBrowserClient } from "@/lib/supabase/client";

export function GoogleOAuthButton() {
  const onClick = async () => {
    const supabase = getSupabaseBrowserClient();
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/api/auth/callback`,
      },
    });
  };

  return (
    <Button type="button" variant="outline" onClick={onClick} className="w-full">
      Continue with Google
    </Button>
  );
}
```

- [ ] **Step 2: Create `apps/web/components/auth/magic-link-form.tsx`**

```typescript
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getSupabaseBrowserClient } from "@/lib/supabase/client";

const schema = z.object({ email: z.string().email("Enter a valid email") });
type FormValues = z.infer<typeof schema>;

export function MagicLinkForm() {
  const [sent, setSent] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    const supabase = getSupabaseBrowserClient();
    const { error } = await supabase.auth.signInWithOtp({
      email: values.email,
      options: { emailRedirectTo: `${window.location.origin}/api/auth/callback` },
    });
    if (error) {
      setServerError(error.message);
      return;
    }
    setSent(true);
  };

  if (sent) {
    return (
      <Alert>
        <AlertDescription>
          Sign-in link sent. Check your email (Mailpit:{" "}
          <a href="http://127.0.0.1:54324" target="_blank" className="underline" rel="noreferrer">
            127.0.0.1:54324
          </a>
          ).
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
      <div className="space-y-2">
        <Label htmlFor="magic-email">Email</Label>
        <Input id="magic-email" type="email" autoComplete="email" {...register("email")} />
        {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
      </div>
      {serverError && (
        <Alert variant="destructive">
          <AlertDescription>{serverError}</AlertDescription>
        </Alert>
      )}
      <Button type="submit" variant="outline" disabled={isSubmitting} className="w-full">
        {isSubmitting ? "Sending..." : "Email me a sign-in link"}
      </Button>
    </form>
  );
}
```

- [ ] **Step 3: Update `signup/page.tsx` + `login/page.tsx`**

Both pages get a "Or" divider + the OAuth button + the magic-link form. Update signup `CardContent` to include:

```typescript
<CardContent className="space-y-4">
  <EmailPasswordForm mode="signup" />
  <div className="relative">
    <Separator />
    <span className="absolute left-1/2 -translate-x-1/2 -translate-y-1/2 bg-card px-2 text-xs text-muted-foreground">
      OR
    </span>
  </div>
  <GoogleOAuthButton />
  <MagicLinkForm />
  <p className="text-center text-sm text-muted-foreground">
    Already have an account?{" "}
    <Link href="/login" className="text-primary underline-offset-4 hover:underline">
      Sign in
    </Link>
  </p>
</CardContent>
```

Add imports at top:
```typescript
import { GoogleOAuthButton } from "@/components/auth/oauth-buttons";
import { MagicLinkForm } from "@/components/auth/magic-link-form";
import { Separator } from "@/components/ui/separator";
```

Apply the same pattern to `login/page.tsx` (replace its CardContent similarly, keeping the "Forgot password?" + "Create account" links at the bottom).

- [ ] **Step 4: (Optional, only if Google OAuth creds set up) Enable Google in Supabase config**

In `infra/supabase/config.toml`, locate `[auth.external.google]` and set:
```toml
[auth.external.google]
enabled = true
client_id = "env(SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_ID)"
secret = "env(SUPABASE_AUTH_EXTERNAL_GOOGLE_SECRET)"
redirect_uri = ""
```

Add to `infra/supabase/.env` (local, gitignored — create if missing):
```bash
SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_ID=<your-client-id>.apps.googleusercontent.com
SUPABASE_AUTH_EXTERNAL_GOOGLE_SECRET=<your-client-secret>
```

Restart: `pnpm db:stop && pnpm db:start`.

If you don't have Google creds: skip this step. The button will still render but clicking it shows a Supabase error — acceptable for M3 demo.

- [ ] **Step 5: Verify build**

```bash
cd c:/gold-leaf-resume && pnpm typecheck
```

- [ ] **Step 6: Commit**

```bash
cd c:/gold-leaf-resume && git add apps/web/ infra/supabase/
git commit -m "feat(web): add Google OAuth + magic link options to /signup + /login"
```

---

## Task 6: Email verification + password reset flows

**Files:**
- Create: `apps/web/app/(auth)/verify/page.tsx`
- Create: `apps/web/app/(auth)/forgot-password/page.tsx`
- Create: `apps/web/app/(auth)/reset-password/page.tsx`

The OAuth callback at `/api/auth/callback` already handles email verification — clicking the link from Mailpit hits that route. But the user may land on `/verify?error=...` if something went wrong; the page exists to display the error.

- [ ] **Step 1: Create `apps/web/app/(auth)/verify/page.tsx`**

```typescript
import Link from "next/link";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default async function VerifyPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const params = await searchParams;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Email verification</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {params.error ? (
          <Alert variant="destructive">
            <AlertDescription>{params.error}</AlertDescription>
          </Alert>
        ) : (
          <p className="text-sm text-muted-foreground">
            Check your inbox for a verification link. Click it to confirm your email.
          </p>
        )}
        <Button asChild variant="outline" className="w-full">
          <Link href="/login">Back to sign in</Link>
        </Button>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Create `apps/web/app/(auth)/forgot-password/page.tsx`**

```typescript
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getSupabaseBrowserClient } from "@/lib/supabase/client";

const schema = z.object({ email: z.string().email("Enter a valid email") });
type FormValues = z.infer<typeof schema>;

export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    const supabase = getSupabaseBrowserClient();
    const { error } = await supabase.auth.resetPasswordForEmail(values.email, {
      redirectTo: `${window.location.origin}/reset-password`,
    });
    if (error) {
      setServerError(error.message);
      return;
    }
    setSent(true);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Forgot password?</CardTitle>
        <CardDescription>We'll email you a reset link.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {sent ? (
          <Alert>
            <AlertDescription>
              Reset link sent. Check Mailpit at{" "}
              <a href="http://127.0.0.1:54324" className="underline" target="_blank" rel="noreferrer">
                127.0.0.1:54324
              </a>
              .
            </AlertDescription>
          </Alert>
        ) : (
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" autoComplete="email" {...register("email")} />
              {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
            </div>
            {serverError && (
              <Alert variant="destructive">
                <AlertDescription>{serverError}</AlertDescription>
              </Alert>
            )}
            <Button type="submit" disabled={isSubmitting} className="w-full">
              {isSubmitting ? "Sending..." : "Send reset link"}
            </Button>
          </form>
        )}
        <Link
          href="/login"
          className="block text-center text-sm text-muted-foreground hover:underline"
        >
          Back to sign in
        </Link>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 3: Create `apps/web/app/(auth)/reset-password/page.tsx`**

```typescript
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getSupabaseBrowserClient } from "@/lib/supabase/client";

const schema = z
  .object({
    password: z.string().min(8, "At least 8 characters"),
    confirm: z.string(),
  })
  .refine((v) => v.password === v.confirm, {
    message: "Passwords don't match",
    path: ["confirm"],
  });
type FormValues = z.infer<typeof schema>;

export default function ResetPasswordPage() {
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    const supabase = getSupabaseBrowserClient();
    const { error } = await supabase.auth.updateUser({ password: values.password });
    if (error) {
      setServerError(error.message);
      return;
    }
    setSuccess(true);
    setTimeout(() => router.push("/login"), 1500);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Set a new password</CardTitle>
        <CardDescription>Choose something at least 8 characters long.</CardDescription>
      </CardHeader>
      <CardContent>
        {success ? (
          <Alert>
            <AlertDescription>Password updated. Redirecting to sign in…</AlertDescription>
          </Alert>
        ) : (
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="password">New password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="new-password"
                {...register("password")}
              />
              {errors.password && (
                <p className="text-xs text-destructive">{errors.password.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirm">Confirm password</Label>
              <Input
                id="confirm"
                type="password"
                autoComplete="new-password"
                {...register("confirm")}
              />
              {errors.confirm && (
                <p className="text-xs text-destructive">{errors.confirm.message}</p>
              )}
            </div>
            {serverError && (
              <Alert variant="destructive">
                <AlertDescription>{serverError}</AlertDescription>
              </Alert>
            )}
            <Button type="submit" disabled={isSubmitting} className="w-full">
              {isSubmitting ? "Updating..." : "Update password"}
            </Button>
          </form>
        )}
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 4: Verify**

```bash
cd c:/gold-leaf-resume && pnpm typecheck
```

- [ ] **Step 5: Commit**

```bash
cd c:/gold-leaf-resume && git add apps/web/
git commit -m "feat(web): /verify + /forgot-password + /reset-password pages"
```

---

## Task 7: /accept-consent page

**Files:**
- Create: `apps/web/components/consent/consent-form.tsx`
- Create: `apps/web/app/accept-consent/page.tsx`

- [ ] **Step 1: Create `apps/web/components/consent/consent-form.tsx`**

```typescript
"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { useGrantConsent, useMe } from "@/lib/api/hooks";
import { ALL_CONSENT_KINDS, REQUIRED_CONSENT_KINDS, type ConsentKind } from "@/lib/consent";

const CONSENT_VERSION = "2026-05-18";

const KIND_LABELS: Record<ConsentKind, { title: string; body: string }> = {
  tos: {
    title: "Terms of Service",
    body: "I have read and agree to the Terms of Service.",
  },
  privacy_policy: {
    title: "Privacy Policy",
    body: "I have read and agree to the Privacy Policy.",
  },
  sensitive_data_au: {
    title: "Sensitive data (AU Privacy Act)",
    body:
      "I consent to Gold Leaf Resume processing sensitive information (including any " +
      "neurodivergence-related details I choose to share) for the purpose of providing the " +
      "service. I understand I can revoke this consent at any time, which will disable " +
      "features that rely on this data.",
  },
  marketing_email: {
    title: "Marketing email (optional)",
    body: "Send me product updates and tips. (Off by default; toggle at any time.)",
  },
};

export function ConsentForm() {
  const router = useRouter();
  const { data: me, isLoading } = useMe();
  const grant = useGrantConsent();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<Record<ConsentKind, boolean>>({
    tos: false,
    privacy_policy: false,
    sensitive_data_au: false,
    marketing_email: false,
  });

  // Hydrate from server state when /v1/me arrives.
  const initial = me?.consent_status;
  const checked = (kind: ConsentKind) =>
    pending[kind] || Boolean(initial?.[kind as keyof typeof initial]);

  const toggle = (kind: ConsentKind) => {
    setPending((p) => ({ ...p, [kind]: !checked(kind) }));
  };

  const allRequiredChecked = REQUIRED_CONSENT_KINDS.every((k) => checked(k));

  const onSubmit = async () => {
    setError(null);
    try {
      for (const kind of ALL_CONSENT_KINDS) {
        const desired = checked(kind);
        const current = Boolean(initial?.[kind as keyof typeof initial]);
        if (desired !== current) {
          await grant.mutateAsync({ kind, version: CONSENT_VERSION, granted: desired });
        }
      }
      router.push("/app/dashboard");
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to record consent.");
    }
  };

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading…</p>;
  }

  return (
    <div className="space-y-4">
      {ALL_CONSENT_KINDS.map((kind) => {
        const info = KIND_LABELS[kind];
        const isRequired = (REQUIRED_CONSENT_KINDS as readonly string[]).includes(kind);
        return (
          <div key={kind} className="flex items-start gap-3 rounded-md border p-3">
            <input
              id={`consent-${kind}`}
              type="checkbox"
              checked={checked(kind)}
              onChange={() => toggle(kind)}
              className="mt-1 h-4 w-4"
            />
            <div className="flex-1">
              <Label htmlFor={`consent-${kind}`} className="cursor-pointer font-medium">
                {info.title}
                {isRequired && <span className="text-destructive"> *</span>}
              </Label>
              <p className="mt-1 text-sm text-muted-foreground">{info.body}</p>
            </div>
          </div>
        );
      })}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <Button
        onClick={onSubmit}
        disabled={!allRequiredChecked || grant.isPending}
        className="w-full"
      >
        {grant.isPending ? "Recording..." : "Continue"}
      </Button>
      <p className="text-center text-xs text-muted-foreground">
        Required items marked <span className="text-destructive">*</span>. You can revoke any
        consent later from Settings.
      </p>
    </div>
  );
}
```

- [ ] **Step 2: Create `apps/web/app/accept-consent/page.tsx`**

```typescript
import { redirect } from "next/navigation";

import { ConsentForm } from "@/components/consent/consent-form";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getSupabaseServerClient } from "@/lib/supabase/server";

export default async function AcceptConsentPage() {
  const supabase = await getSupabaseServerClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  return (
    <div className="flex min-h-screen items-start justify-center bg-background px-4 py-12">
      <div className="w-full max-w-2xl">
        <Card>
          <CardHeader>
            <CardTitle>Accept consent</CardTitle>
            <CardDescription>
              We need these before you can use Gold Leaf Resume. Sensitive-data consent enables
              ND-aware features.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ConsentForm />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Verify**

```bash
cd c:/gold-leaf-resume && pnpm typecheck
```

- [ ] **Step 4: Commit**

```bash
cd c:/gold-leaf-resume && git add apps/web/
git commit -m "feat(web): /accept-consent page wired to /v1/me/consent"
```

---

## Task 8: Authenticated /app shell layout + empty pages

**Files:**
- Create: `apps/web/components/app/top-bar.tsx`
- Create: `apps/web/components/app/sidebar.tsx`
- Create: `apps/web/components/auth/logout-button.tsx`
- Create: `apps/web/app/app/layout.tsx`
- Create: `apps/web/app/app/dashboard/page.tsx`
- Create: `apps/web/app/app/resumes/page.tsx`
- Create: `apps/web/app/app/jds/page.tsx`
- Create: `apps/web/app/app/cover-letters/page.tsx`
- Create: `apps/web/app/app/applications/page.tsx`
- Create: `apps/web/app/app/analytics/page.tsx`
- Create: `apps/web/app/app/pacing/page.tsx`
- Create: `apps/web/app/app/settings/page.tsx`

- [ ] **Step 1: Create `apps/web/components/auth/logout-button.tsx`**

```typescript
"use client";

import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { getSupabaseBrowserClient } from "@/lib/supabase/client";

export function LogoutButton() {
  const router = useRouter();
  const onClick = async () => {
    const supabase = getSupabaseBrowserClient();
    await supabase.auth.signOut();
    router.push("/login");
    router.refresh();
  };
  return (
    <Button variant="ghost" size="sm" onClick={onClick}>
      Sign out
    </Button>
  );
}
```

- [ ] **Step 2: Create `apps/web/components/app/top-bar.tsx`**

```typescript
"use client";

import Link from "next/link";

import { LogoutButton } from "@/components/auth/logout-button";
import { useMe } from "@/lib/api/hooks";

export function TopBar() {
  const { data: me } = useMe();
  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-background px-4">
      <Link href="/app/dashboard" className="flex items-center gap-2">
        <span className="text-lg font-semibold">
          <span className="text-goldleaf-500">Gold Leaf</span> Resume
        </span>
      </Link>
      <div className="flex items-center gap-4 text-sm text-muted-foreground">
        {me && <span>{me.email}</span>}
        <LogoutButton />
      </div>
    </header>
  );
}
```

- [ ] **Step 3: Create `apps/web/components/app/sidebar.tsx`**

```typescript
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const NAV_SECTIONS = [
  {
    title: "1 · Apply",
    items: [
      { href: "/app/applications", label: "Applications" },
      { href: "/app/jds", label: "JDs" },
    ],
  },
  {
    title: "2 · Build",
    items: [
      { href: "/app/resumes", label: "Resumes" },
      { href: "/app/cover-letters", label: "Cover letters" },
    ],
  },
  {
    title: "3 · Track",
    items: [
      { href: "/app/analytics", label: "Analytics" },
      { href: "/app/pacing", label: "Pacing" },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="w-56 shrink-0 border-r border-border bg-background p-4">
      <nav className="space-y-6 text-sm">
        <Link
          href="/app/dashboard"
          className={cn(
            "block rounded-md px-3 py-2 transition-colors hover:bg-accent hover:text-accent-foreground",
            pathname === "/app/dashboard" && "bg-accent text-accent-foreground font-medium",
          )}
        >
          Overview
        </Link>
        {NAV_SECTIONS.map((section) => (
          <div key={section.title}>
            <div className="px-3 py-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              {section.title}
            </div>
            <ul className="mt-1 space-y-0.5">
              {section.items.map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className={cn(
                      "block rounded-md px-3 py-2 transition-colors hover:bg-accent hover:text-accent-foreground",
                      pathname === item.href && "bg-accent text-accent-foreground font-medium",
                    )}
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
        <div className="border-t border-border pt-4">
          <Link
            href="/app/settings"
            className={cn(
              "block rounded-md px-3 py-2 transition-colors hover:bg-accent hover:text-accent-foreground",
              pathname === "/app/settings" && "bg-accent text-accent-foreground font-medium",
            )}
          >
            Settings
          </Link>
        </div>
      </nav>
    </aside>
  );
}
```

- [ ] **Step 4: Create `apps/web/app/app/layout.tsx`** (consent check happens here, server-side)

```typescript
import { redirect } from "next/navigation";

import { Sidebar } from "@/components/app/sidebar";
import { TopBar } from "@/components/app/top-bar";
import { env } from "@/lib/env";
import { REQUIRED_CONSENT_KINDS } from "@/lib/consent";
import { getSupabaseServerClient } from "@/lib/supabase/server";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const supabase = await getSupabaseServerClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) redirect("/login");

  // Authoritative consent check via the API.
  const meRes = await fetch(`${env.NEXT_PUBLIC_API_URL}/v1/me`, {
    headers: { Authorization: `Bearer ${session.access_token}` },
    cache: "no-store",
  });
  if (!meRes.ok) {
    if (meRes.status === 401) redirect("/login");
    throw new Error(`Failed to fetch /v1/me: ${meRes.status}`);
  }
  const me = (await meRes.json()) as {
    consent_status: Record<string, boolean>;
  };
  const missing = REQUIRED_CONSENT_KINDS.filter((k) => !me.consent_status[k]);
  if (missing.length > 0) {
    redirect("/accept-consent");
  }

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <TopBar />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Create empty placeholder pages**

For each of `dashboard`, `resumes`, `jds`, `cover-letters`, `applications`, `analytics`, `pacing`, `settings`, create `apps/web/app/app/<slug>/page.tsx` with content like:

```typescript
export default function DashboardPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Overview</h1>
      <p className="text-sm text-muted-foreground">Coming soon — SP2 will populate this.</p>
    </div>
  );
}
```

Adjust the `<h1>` text and the "SP[N] will populate this" tagline per page:
- `dashboard/page.tsx` — Overview — "SP2 will populate this."
- `resumes/page.tsx` — Resumes — "SP2 (Resumes vertical) will populate this."
- `jds/page.tsx` — JDs — "SP3 (JDs + Tailor + Cover letter) will populate this."
- `cover-letters/page.tsx` — Cover letters — "SP3 will populate this."
- `applications/page.tsx` — Applications — "SP4 (Application loop) will populate this."
- `analytics/page.tsx` — Analytics — "SP4 will populate this."
- `pacing/page.tsx` — Pacing — "SP4 will populate this."
- `settings/page.tsx` — Settings — "SP1·M6 will populate this."

- [ ] **Step 6: Verify**

```bash
cd c:/gold-leaf-resume && pnpm typecheck
```

- [ ] **Step 7: Commit**

```bash
cd c:/gold-leaf-resume && git add apps/web/
git commit -m "feat(web): authenticated /app shell + sidebar + top bar + 8 placeholder pages"
```

---

## Task 9: Next.js middleware (auth fast-path)

**Files:**
- Create: `apps/web/middleware.ts`

The server-side layout in Task 8 already enforces session + consent for `/app/*`. The middleware adds a faster path that catches the no-session case before any data fetching happens.

- [ ] **Step 1: Create `apps/web/middleware.ts`**

```typescript
import { NextResponse, type NextRequest } from "next/server";

import { updateSupabaseSession } from "@/lib/supabase/middleware";

export async function middleware(request: NextRequest) {
  const { response, user } = await updateSupabaseSession(request);

  const path = request.nextUrl.pathname;
  const isAppRoute = path.startsWith("/app");
  const isAuthRoute =
    path === "/login" ||
    path === "/signup" ||
    path === "/forgot-password" ||
    path === "/reset-password" ||
    path === "/verify";

  if (isAppRoute && !user) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  if (isAuthRoute && user) {
    // Logged-in user hitting /login or /signup → bounce to app.
    // /reset-password is the exception (user may be authed mid-reset).
    if (path !== "/reset-password") {
      return NextResponse.redirect(new URL("/app/dashboard", request.url));
    }
  }

  return response;
}

export const config = {
  matcher: [
    // Run on every path except Next internals + static assets.
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
```

- [ ] **Step 2: Verify build**

```bash
cd c:/gold-leaf-resume && pnpm typecheck
```

- [ ] **Step 3: Manual smoke test**

Start everything (api, web, db). Visit `/app/dashboard` in a private window. Should redirect to `/login`. Sign in with a verified user. Should redirect to `/app/dashboard` (or `/accept-consent` first if pending).

- [ ] **Step 4: Commit**

```bash
cd c:/gold-leaf-resume && git add apps/web/middleware.ts
git commit -m "feat(web): Next.js middleware enforces auth on /app/* + bounces authed users off /login"
```

---

## Task 10: /legal/* stubs + landing page polish

**Files:**
- Modify: `apps/web/app/page.tsx`
- Create: `apps/web/app/legal/terms/page.tsx`
- Create: `apps/web/app/legal/privacy/page.tsx`
- Create: `apps/web/app/legal/cookies/page.tsx`

- [ ] **Step 1: Update landing page**

Replace `apps/web/app/page.tsx`:
```typescript
import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-6 py-12">
      <div className="max-w-2xl text-center">
        <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
          <span className="text-goldleaf-500">Gold Leaf</span> Resume
        </h1>
        <p className="mt-6 text-lg text-muted-foreground">
          ND-aware resume and job-application management. Currently in private development.
        </p>
        <div className="mt-8 flex justify-center gap-4">
          <Button asChild>
            <Link href="/signup">Sign up</Link>
          </Button>
          <Button asChild variant="outline">
            <Link href="/login">Sign in</Link>
          </Button>
        </div>
        <p className="mt-16 text-sm text-muted-foreground/70">
          A shard product under <span className="font-medium">BRAINS Incubator</span>.
        </p>
        <nav className="mt-8 flex justify-center gap-4 text-xs text-muted-foreground">
          <Link href="/legal/terms" className="hover:underline">
            Terms
          </Link>
          <Link href="/legal/privacy" className="hover:underline">
            Privacy
          </Link>
          <Link href="/legal/cookies" className="hover:underline">
            Cookies
          </Link>
        </nav>
      </div>
    </main>
  );
}
```

- [ ] **Step 2: Create `apps/web/app/legal/terms/page.tsx`**

```typescript
export default function TermsPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="text-3xl font-semibold">Terms of Service</h1>
      <p className="mt-2 text-sm text-muted-foreground">Last updated: 2026-05-18 — DRAFT</p>
      <div className="prose prose-sm mt-6 space-y-4 text-foreground">
        <p>
          This is a placeholder document. Final terms will be published at launch. By using Gold
          Leaf Resume during this private development phase, you agree to use the service for
          personal testing only and not to submit complaints regarding incomplete features.
        </p>
        <p>
          Real terms will cover: account creation, acceptable use, data retention, intellectual
          property, warranty disclaimers, liability limits, and termination.
        </p>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create `apps/web/app/legal/privacy/page.tsx`**

```typescript
export default function PrivacyPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="text-3xl font-semibold">Privacy Policy</h1>
      <p className="mt-2 text-sm text-muted-foreground">Last updated: 2026-05-18 — DRAFT</p>
      <div className="prose prose-sm mt-6 space-y-4 text-foreground">
        <p>
          This is a placeholder document. Final privacy policy will be published at launch.
        </p>
        <p>
          Real policy will cover: what data we collect, how we use it, how long we retain it,
          your rights under the Australian Privacy Principles (APPs) and GDPR (once we expand
          to UK/EU), third-party processors (Supabase, Fly.io, Anthropic), how to export or
          delete your data, and how to revoke consent.
        </p>
        <p>
          Sensitive information (including any neurodivergence-related details) is processed
          only with your explicit consent, per APP 3.
        </p>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Create `apps/web/app/legal/cookies/page.tsx`**

```typescript
export default function CookiesPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="text-3xl font-semibold">Cookies</h1>
      <p className="mt-2 text-sm text-muted-foreground">Last updated: 2026-05-18 — DRAFT</p>
      <div className="prose prose-sm mt-6 space-y-4 text-foreground">
        <p>
          This is a placeholder document. We currently use cookies only for authentication
          (Supabase session cookies). No analytics or advertising cookies are set.
        </p>
        <p>
          A real cookies policy will be published at launch, including any analytics tooling
          we adopt.
        </p>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Verify + commit**

```bash
cd c:/gold-leaf-resume && pnpm typecheck
git add apps/web/
git commit -m "feat(web): landing page polish + /legal/{terms,privacy,cookies} stub pages"
```

---

## Task 11: Component tests (Vitest)

**Files:**
- Modify: `apps/web/tests/home.test.tsx` (the new landing page changed)
- Create: `apps/web/tests/components/consent-form.test.tsx`
- Create: `apps/web/tests/components/email-password-form.test.tsx`

(Full E2E via Playwright deferred to SP7 to keep M3 scope manageable. Vitest component tests prove the forms render + validate.)

- [ ] **Step 1: Update `home.test.tsx`** — the new landing has CTA buttons. Update assertions:

```typescript
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

  it("renders sign-up and sign-in CTAs", () => {
    render(<Home />);
    expect(screen.getByRole("link", { name: /sign up/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /sign in/i })).toBeInTheDocument();
  });

  it("renders legal nav", () => {
    render(<Home />);
    expect(screen.getByRole("link", { name: /^terms$/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /^privacy$/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /^cookies$/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Create `apps/web/tests/components/email-password-form.test.tsx`**

```typescript
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

// Mock the Supabase client + router before importing the component.
vi.mock("@/lib/supabase/client", () => ({
  getSupabaseBrowserClient: () => ({
    auth: {
      signUp: vi.fn().mockResolvedValue({ error: null }),
      signInWithPassword: vi.fn().mockResolvedValue({ error: null }),
    },
  }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

import { EmailPasswordForm } from "@/components/auth/email-password-form";

describe("EmailPasswordForm", () => {
  it("validates email format", async () => {
    const user = userEvent.setup();
    render(<EmailPasswordForm mode="signup" />);
    await user.type(screen.getByLabelText(/email/i), "not-an-email");
    await user.type(screen.getByLabelText(/password/i), "12345678");
    await user.click(screen.getByRole("button", { name: /create account/i }));
    expect(await screen.findByText(/enter a valid email/i)).toBeInTheDocument();
  });

  it("validates password length", async () => {
    const user = userEvent.setup();
    render(<EmailPasswordForm mode="signup" />);
    await user.type(screen.getByLabelText(/email/i), "ok@example.com");
    await user.type(screen.getByLabelText(/password/i), "short");
    await user.click(screen.getByRole("button", { name: /create account/i }));
    expect(await screen.findByText(/at least 8 characters/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Create `apps/web/tests/components/consent-form.test.tsx`**

```typescript
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

// Mock useMe + useGrantConsent to control state without a real API.
vi.mock("@/lib/api/hooks", () => ({
  useMe: () => ({
    data: {
      consent_status: {
        tos: false,
        privacy_policy: false,
        sensitive_data_au: false,
        marketing_email: false,
      },
    },
    isLoading: false,
  }),
  useGrantConsent: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

import { ConsentForm } from "@/components/consent/consent-form";

function renderWithRQ(ui: React.ReactNode) {
  const client = new QueryClient();
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("ConsentForm", () => {
  it("disables Continue until all required consents are checked", async () => {
    renderWithRQ(<ConsentForm />);
    const continueBtn = screen.getByRole("button", { name: /continue/i });
    expect(continueBtn).toBeDisabled();
  });

  it("lists all four consent kinds", () => {
    renderWithRQ(<ConsentForm />);
    expect(screen.getByText(/terms of service/i)).toBeInTheDocument();
    expect(screen.getByText(/privacy policy/i)).toBeInTheDocument();
    expect(screen.getByText(/sensitive data/i)).toBeInTheDocument();
    expect(screen.getByText(/marketing email/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: Add testing-library/user-event dev dep**

In `apps/web/package.json` `devDependencies`:
```json
    "@testing-library/user-event": "14.5.2"
```

```bash
cd c:/gold-leaf-resume && pnpm install
```

- [ ] **Step 5: Run tests**

```bash
cd c:/gold-leaf-resume && pnpm --filter web test
```
Expected: ~9 tests pass (4 home + 2 EmailPasswordForm + 2 ConsentForm + 1 from existing).

- [ ] **Step 6: Commit**

```bash
cd c:/gold-leaf-resume && git add apps/web/ pnpm-lock.yaml
git commit -m "test(web): home + EmailPasswordForm + ConsentForm component tests"
```

---

## Task 12: Open PR + CI green + squash-merge

- [ ] **Step 1: Push branch**

```bash
cd c:/gold-leaf-resume && git push -u origin m3-frontend-auth-consent
```

- [ ] **Step 2: Open PR**

```bash
gh pr create --title "SP1·M3 — Frontend auth + consent flows" --base main --head m3-frontend-auth-consent --body "$(cat <<'EOF'
## Summary
- Supabase SSR client wired across browser/server/middleware
- Auth pages: /signup, /login (email/password + Google OAuth + magic link), /verify, /forgot-password, /reset-password
- OAuth/magic-link callback at /api/auth/callback
- /accept-consent page: 4 toggles, POSTs to /v1/me/consent
- Authenticated /app shell: top bar + journey-stage sidebar + 8 placeholder pages
- Server-side layout enforces session + consent on /app/*; Next.js middleware does the auth fast-path
- /legal/{terms,privacy,cookies} stub pages
- Landing page polish with sign-up/sign-in CTAs
- 6 shadcn/ui components installed (button, input, label, card, alert, separator)
- Design tokens now live in packages/design-tokens (Tailwind imports them)
- 9 Vitest tests; typecheck clean; CI green

## Test plan
- [x] /signup with email/password → verify email → /accept-consent → /app/dashboard
- [x] /login with verified user → /app/dashboard
- [x] Private window hitting /app/* → /login
- [x] Logged-in user without consent → /accept-consent
- [x] Forgot password flow via Mailpit
- [x] Magic link flow via Mailpit
- [ ] Google OAuth (only if creds set up)
- [x] CI green on all jobs

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 3: Wait for CI**

```bash
gh pr checks --watch
```

Fix any CI failures locally → commit → push → re-watch.

- [ ] **Step 4: Squash-merge**

```bash
gh pr merge --squash --delete-branch
git checkout main && git pull
```

---

## Task 13: Tag sp1-m3 + update spec status

- [ ] **Step 1: Tag**

```bash
cd c:/gold-leaf-resume && git tag -a sp1-m3 -m "SP1·M3 — Frontend auth + consent flows. Signup/login/verify/reset/forgot/accept-consent + authenticated /app shell + middleware + 9 Vitest tests."
git push --tags
```

- [ ] **Step 2: Update SP1 spec status** in `c:/Brains_Resume_Skill/docs/specs/2026-05-18-sp1-gold-leaf-resume-platform-foundation.md`:

Find:
```markdown
**Status:** In implementation — SP1·M0 + M1 + M2 complete (2026-05-18 — `sp1-m0`, `sp1-m1`, `sp1-m2` tags in `gold-leaf-resume`); M3 (Frontend auth + consent flows) next.
```

Replace with:
```markdown
**Status:** In implementation — SP1·M0 + M1 + M2 + M3 complete (2026-05-18 — `sp1-m0`, `sp1-m1`, `sp1-m2`, `sp1-m3` tags in `gold-leaf-resume`); M4 (LLM abstraction + vault) next.
```

- [ ] **Step 3: Commit + push**

```bash
cd c:/Brains_Resume_Skill && git add docs/specs/2026-05-18-sp1-gold-leaf-resume-platform-foundation.md
git commit -m "docs: mark SP1·M3 complete in spec status"
git push
```

---

## Self-review

**Spec coverage** (vs SP1 spec §4.2 + §4.7):

| Spec section | M3 coverage |
|---|---|
| §4.2 Next.js + TS strict + Tailwind + shadcn/ui | ✓ Tasks 1-3 |
| §4.2 Supabase JS via @supabase/ssr | ✓ Task 2 |
| §4.2 react-query | ✓ Task 3 |
| §4.2 typed API client | ✓ Task 3 (openapi-fetch + shared-types) |
| §4.2 routes (/signup, /login, /verify, /reset-password, /accept-consent) | ✓ Tasks 4-7 |
| §4.2 authenticated /app/* shell | ✓ Task 8 |
| §4.2 sidebar nav (journey-stage 1/2/3) | ✓ Task 8 |
| §4.2 design tokens package populated | ✓ Task 1 |
| §4.2 accessibility baseline (WCAG 2.1 AA) | partial — shadcn primitives are accessible, formal audit defers to SP7 |
| §4.7 sign up + verify + accept consent + /app | ✓ Tasks 4-9 |
| §4.7 consent gate redirects | ✓ Task 8 (server-side) + Task 9 (middleware) |
| §4.7 Apple Sign-In / passkeys | ✗ deferred (post-v1) |
| §4.7 Account deletion + data export UI | ✗ deferred to M6 (Settings) |

**Placeholder scan:** No `TBD`/`TODO`. Every code block is full code.

**Type consistency:** `consent_status` shape matches between frontend (`@goldleafresume/shared-types`) and backend (`apps/api/src/schemas/me.py`). The `REQUIRED_CONSENT_KINDS` constant exists in both places — they must stay in sync; the plan flags this.

**Known shortcuts to revisit:**
- Google OAuth is gated behind manual Cloud Console setup (Task 5 Step 4). Marketable workaround: magic link covers most user flows.
- Playwright E2E tests deferred to SP7 — Vitest component tests cover the form-rendering surface.
- Token-refresh edge cases (e.g., refresh token expired) — Supabase + the middleware handle it; UX for "session expired, please sign in" not yet polished.

**Pre-flight gotchas:**
- `apps/web/.env.local` must exist with the Supabase Publishable key BEFORE running any pnpm command that boots Next.js. CI does its own env setup.
- `infra/supabase/config.toml` `site_url = "http://127.0.0.1:3000"` is critical — without it, magic-link + reset-password redirect URLs land at Supabase's default (`http://localhost:3000`), which works on macOS/Linux but can be fragile on Windows.
- Server-side fetch from `/app/layout.tsx` calls the API. If the API isn't running, `/app/*` returns 500. Real users see this only during the brief window between deploys; SP7 may add a friendlier error page.

---

**End of SP1·M3 plan.**
