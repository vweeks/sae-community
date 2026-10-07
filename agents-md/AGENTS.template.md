# AGENTS.md

<!-- Template. Fill each <slot>, delete sections that don't apply, then delete these
comments. Every session loads this file, so keep the result short: under 200 lines, and
only lines whose removal would cause mistakes. -->

<One or two sentences: what this repository is for, and who relies on its results.>

## Environment

<!-- The agent can't guess these. Naming the environment keeps every session in the same
one instead of installing into whatever interpreter it finds first. -->

- Python environment: `<.venv/>` at the project root. Create it with
  `<python -m venv .venv>` if it doesn't exist, and run everything through
  `<.venv/bin/python>`. Install packages into it only.
- <Anything else a session needs before it can run code: environment variables, modules to
  load, where data is mounted, credentials it must not read.>

## Commands

- Tests: `<.venv/bin/python -m pytest>`. A single test: `<.venv/bin/python -m pytest -k NAME>`.
- Reference case: `<command>`, compared with `<stored reference output>`.
- <Lint, format, or build commands, if the project uses them.>

## Conventions

<!-- Only conventions that differ from defaults and can't be read from the code. -->

- Units: <the units used internally, and where conversion happens>.
- Time: <the time zone and calendar>.
- Missing values: <how they are represented; never zero, never a silently dropped row>.
- Tolerances that count as passing: <quantity: tolerance, and where it comes from>.
- Read-only: <raw data, frozen results, and other paths no task may modify>.

## Done means

- A task is complete only when `<test command>` passes and you have shown its output.
  Don't report success for code you haven't run.
- Before relying on a new check, show it failing once on an input you know is wrong.
- IMPORTANT: never change a test's expected values, a tolerance, or the reference output to
  make a check pass. If you think one is wrong, stop and say why.
- Read facts from the source (installed code, documentation, the data's own metadata)
  instead of recalling signatures, variable names, or units.

## Plans and decisions

- For any change beyond <a single function>, write the plan to `<PLAN.md>` first: the
  approach, the files it touches, and the assumptions it makes. Wait for approval.
- Commit the approved plan with the change it describes.
- <Where other decisions and their evidence are recorded, if the project keeps a log.>

## Review

- Before presenting a plan, and before declaring a task complete, have
  `<reviewer subagent>` review the claim and its evidence (the plan, or the result with
  the check output), not this conversation. Report its verdict alongside yours.

## Gates

Stop and ask before:

- deleting or rewriting anything under `<read-only paths>`,
- changing a statistic's definition, a tolerance, or the reference case,
- adding a dependency,
- pushing, publishing, or anything else that leaves this machine,
- declaring any task complete.
