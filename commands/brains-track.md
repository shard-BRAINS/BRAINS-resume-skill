---
description: Manage the application tracker — add applications, log outcomes, view pipeline summary
argument-hint: <subcommand> [args...] — subcommands: add | update <id> <event> | list [--company X] [--since YYYY-MM-DD] [--status open|closed] | summary | focus-areas | healthy-rate
---

<!-- markdownlint-disable-file MD041 -->
Run the BRAINS Resume Skill application tracker. Parse `$ARGUMENTS` for the subcommand and route to the matching Python helper in `scripts/tracker/`. All output is markdown rendered in chat, carrying the BRAINS coaching artifact frame.

## Subcommand routing

- **`add`** — interactive add of an application that was submitted without going through `brains-precheck`. Walk through the same six questions as the precheck workflow (see `references/workflows/pre-application-check.md`), then call `scripts/tracker/add.py:add_application`.

- **`update <id> <event-type> [date] [notes]`** — log an outcome on an existing application. Valid event-types: `acknowledged`, `callback`, `phone_screen`, `first_round`, `second_round`, `take_home`, `offer`, `rejection`, `ghosted`, `withdrew`. Call `scripts/tracker/add.py:record_outcome`.

- **`list [--company X] [--since YYYY-MM-DD] [--status open|closed]`** — call `scripts/tracker/query.py:list_applications` with the given filters and render the result as a markdown table.

- **`summary`** — call `scripts/tracker/query.py:weekly_summary` and `efficacy_by_template`. Render:
  - Pipeline funnel (applications → callbacks → interviews → offers/rejections)
  - This-week pacing vs the user's healthy weekly rate
  - Per-template efficacy table

- **`focus-areas`** — view or edit `~/.brains-resume/profile.json` focus_areas. If no argument, show the current list. If a comma-separated list is provided, replace via `scripts/tracker/profile.py:write_profile`.

- **`healthy-rate`** — view or set `~/.brains-resume/profile.json` healthy_weekly_rate. If no argument, show the current value. If a number is provided, save via `write_profile`.

## First-time user

If the tracker db doesn't exist yet (any subcommand other than `summary` is the first write), surface the one-time privacy notice:

> "Application data will be stored locally at `~/.brains-resume/tracker.db`. Nothing is transmitted. You can delete the entire directory at any time to remove all tracker history."

Then proceed with the subcommand.

## Branding

The tracker is a BRAINS coaching artifact. Markdown output uses identity-first language, no italics in body text, no third-party org references. Tables follow the existing coaching-report markdown conventions.
