# Contributing to the BRAINS Resume Skill

This project is part of the BRAINS Incubator — a space for community projects from neurodivergent minds, for neurodivergent people. Contributions are welcome from anyone whose work moves the skill closer to that goal.

## Before you contribute

- Read the design specification in `docs/specs/`. It captures every architectural and ethical decision and the reasons behind them. New work should align with it (or argue for changing it).
- Identity-first language is the default ("autistic person," not "person with autism"). Follow an individual's stated preference when they tell you theirs.
- Never use deficit framing in default copy. Never use puzzle-piece imagery. Never use AI-generated images of people.
- Outputs the user submits to employers (resumes, cover letters) stay unbranded. Outputs the user reads as coaching (review reports, disclosure worksheets) carry BRAINS branding.

## How to contribute

1. Open an issue describing the change you have in mind before writing code.
2. Branch from `main`. Keep the branch focused on one concern.
3. Match the conventional-commits style in commit messages (`feat:`, `fix:`, `docs:`, `test:`, `build:`, `chore:`).
4. Run the test suite (`pytest`) before opening a pull request. New features need new tests. The ten-pattern ND-bias coverage rule applies — `bias_scan.py` must detect every pattern in the catalog.
5. Never include third-party project, organisation, or platform credits in code, documentation, or commit messages. BRAINS / BRAINS Trust / BRAINS Incubator attribution only.

## What we are looking for

- New bias patterns observed in real (anonymised) examples, with proposed mitigations
- ATS rule updates as recruiter-tech evolves
- Language do/don't entries from lived experience
- Workflow improvements that reduce friction for users navigating burnout or executive-function load
- Translations and localisations

## What we are not looking for

- Removal or watering-down of the safeguarding caveats in the disclosure framework
- Branding on user-submitted documents
- Telemetry, analytics, or any data exfiltration

— Built by neurodivergent minds, for neurodivergent people.