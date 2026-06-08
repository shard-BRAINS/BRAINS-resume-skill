# Contributing

Thanks for considering a contribution to the BRAINS Resume Skill. This guide tells you what you need to know to send a pull request we can merge quickly.

## Before you start

- Read the [Code of Conduct](CODE_OF_CONDUCT.md). It is the floor, not the ceiling.
- Read the design specs in `docs/specs/`. They capture every architectural and ethical decision and the reasons behind them. New work should align with them, or argue for changing them.
- For non-trivial changes, open an issue first so we can agree on direction before you spend time on it.
- Small fixes (typos, broken links, single-file refactors) do not need an issue first. Just send the pull request.

## How to write a pull request

Each pull request should:

1. **Do one thing.** If you find a second thing, open a second pull request.
2. **State the change in the title.** Not "fix" or "update" — say what changed. Use conventional-commits style (`feat:`, `fix:`, `docs:`, `test:`, `build:`, `chore:`).
3. **Explain the why in the description.** Link the issue if there is one.
4. **Pass all checks.** Security, lint, Vale, readability, markdownlint. All run automatically on your pull request.
5. **Run the test suite.** `pytest` from the repo root. New features need new tests.

## Style

- Match the existing code style. We do not have strong opinions beyond what the linters enforce.
- Prefer clear names over short names.
- Avoid adding dependencies unless you need them.
- Comments explain the **why**. Code explains the **what**.

## Writing for BRAINS

Any prose you add — READMEs, docs, error messages, commit messages — should match the BRAINS voice:

- **Plain language first.** Aim for Grade 8 reading level for anything a user will read.
- **Direct, not blunt.** State the point, then the evidence.
- **No deficit framing.** Vale will flag this. Trust the flag.
- **Identity-first by default.** `autistic users`, not `users with autism`. Follow an individual's stated preference when they tell you theirs.
- **Never** use puzzle-piece imagery, AI-generated images of people, or near-paraphrases of the BRAINS taglines.

The Vale rule pack in `.vale/styles/BRAINS/` encodes these rules. If the linter blocks you and you think it is wrong, open an issue rather than disabling the rule.

## Resume-skill specifics

These rules are particular to this project. They build on, do not replace, the general rules above.

- **Output branding.** Outputs the user submits to employers (résumés, cover letters) stay unbranded. Outputs the user reads as coaching (review reports, disclosure worksheets) carry BRAINS branding.
- **ND-bias catalog.** New bias patterns are welcome — open an issue with the pattern, an anonymised example, and the proposed mitigation. The ten-pattern coverage rule applies — `bias_scan.py` must detect every pattern in the catalog. Add tests with each new pattern.
- **No third-party credits in outputs.** Never include third-party project, organisation, or platform credits in code, documentation, or commit messages. BRAINS / BRAINS Trust / BRAINS Incubator attribution only.
- **Safeguarding in disclosure framework.** Do not remove or water down the safeguarding caveats. They exist because the wrong advice in this area causes real harm.

## What we are looking for

- New ND-bias patterns observed in real (anonymised) examples, with proposed mitigations
- ATS rule updates as recruiter-tech evolves
- Language Do/Don't entries grounded in lived experience
- Workflow improvements that reduce friction for users navigating burnout or executive-function load
- Translations and localisations

## What we are not looking for

- Removal or watering-down of the safeguarding caveats in the disclosure framework
- Branded outputs sent to employers (the unbranded-output rule is deliberate)
- Adoption of person-first phrasing as the default (community preference is identity-first; the existing override path covers individual preference)
- Telemetry, analytics, or any phone-home — the privacy guarantees are unconditional

## Security

Do not include credentials, tokens, or production data in a pull request. Gitleaks will catch most of these. If you find a security issue, follow [SECURITY.md](SECURITY.md) instead of opening an issue.

## Licence

By contributing you agree your work is licensed under the same terms as the project (MIT — see [LICENSE](LICENSE)).

## Questions

Open an issue with the `question` label, or join the [BRAINS Discord](https://discord.gg/BEmTXXscBr).
