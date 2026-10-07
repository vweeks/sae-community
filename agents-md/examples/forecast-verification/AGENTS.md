# AGENTS.md

This repository scores recent weather forecasts against the ERA5 reanalysis.

## Environment

- Python environment: `.venv/` at the project root. Create it with `python -m venv .venv`
  if it doesn't exist, and run everything through `.venv/bin/python`. Install packages
  into it only.
- Data comes from the Open-Meteo Previous Runs and Archive APIs. No key is needed. The free
  tier is for non-commercial use, and every table or figure built from it credits
  Open-Meteo under CC BY 4.0.

## Commands

- Tests: `.venv/bin/python -m pytest`. A single test: `.venv/bin/python -m pytest -k NAME`.

## Conventions

- All internal computation in the API's native units (°C, km/h, mm, %). Report tables and
  figures in °F, mph, inches, and %. Convert once, at the reporting boundary, never
  mid-pipeline.
- All times UTC (timezone=GMT at fetch). A displayed time states its zone.
- Raw API responses under `data/raw/` are read-only once hashed into `PROVENANCE.md`. Every
  claim about what the data says must be checkable against them.
- A null in a response is an explicitly missing value in our records: never zero, never a
  silently dropped row.

## Done means

- A task is complete only when `.venv/bin/python -m pytest` passes and you have shown its
  output. Don't report success for code you haven't run.
- Every statistic has a test on a small case computed by hand.
- Before relying on a new check, show it failing once on an input you know is wrong.
- IMPORTANT: never change a test's expected values, a tolerance, or a statistic's
  definition to make a check pass. If you think one is wrong, stop and say why.
- Read facts from the source (installed code, the API documentation, the response itself)
  instead of recalling parameter names, variable names, or units.

## Skills and review

- Run the `unit-check` skill on each new kind of API response before writing code that
  uses its values.
- Before presenting a plan, and before declaring a task complete, have the `cynic-kyle`
  subagent review the claim and its evidence (the plan, or the result with the test
  output), not this conversation. Report its verdict alongside yours.

## Plan page

- `plan.html` is what I read before approving a plan, so it must be easier to scan than
  terminal output. Give each part of the plan its own heading. Write steps, files, and
  assumptions as lists, and anything with repeated fields (requests, files, series) as a
  table. Put URLs, file paths, and field names in code formatting.
- Before presenting `plan.html`, check the generated HTML: every list and table in
  `PLAN.md` must come out as a list or table, not as a run-on paragraph.
- Commit the approved `PLAN.md` with the change it describes.

## Gates

Stop and ask before:

- deleting or rewriting anything under `data/raw/`,
- changing a statistic's definition or a tolerance,
- adding a dependency,
- pushing, publishing, or anything else that leaves this machine,
- declaring any task complete.
