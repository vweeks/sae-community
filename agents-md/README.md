# AGENTS.md: a project instruction file

Every agent session starts without your project's standing rules. Left to fill the gaps, an
agent picks plausible defaults: it installs packages into whichever interpreter it finds,
reports success from code it hasn't run, edits a test's expected value until the test
passes, or tightens a tolerance nobody asked it to touch. Each choice looks reasonable in
the moment, and nothing in the session says otherwise.

`AGENTS.md` is a plain Markdown file at the root of your repository that the agent reads at
the start of every session. It is the cheapest safeguard you can add: written once, applied
every session, whether or not anyone remembers to mention it.

## What's here

| File | What it is |
|---|---|
| [`AGENTS.template.md`](AGENTS.template.md) | A template for scientific software projects. The rules that carry over to any project are written out; the lines only your project can supply are `<slots>`. |
| [`examples/forecast-verification/AGENTS.md`](examples/forecast-verification/AGENTS.md) | The template filled in for a small project that scores weather forecasts against a reanalysis. |

## Using the template

Copy it to your repository root as `AGENTS.md`, fill the slots, and delete what doesn't
apply. Then test it the way you'd test code: start a fresh session, give it a task, and
watch whether its behavior actually changes. When the agent ignores a rule, the file is
usually too long or the rule too vague; when it asks something the file already answers,
the wording is ambiguous.

Keep each line only if removing it would cause mistakes. Leave out anything the agent can
read from the code, conventions it already knows, and advice like "write clean code". The
file loads every session, so keep it under about 200 lines; models follow fewer, sharper
lines more reliably. Use emphasis such as "IMPORTANT" on one line at most, or it stops
meaning anything.

## Why each section is there

- **Environment.** The agent can't guess which environment your project uses. Naming it
  (`.venv/` at the root, say) keeps every session in the same one.
- **Commands.** How to run the tests and the reference case. These are the lines an agent
  most often gets wrong by guessing.
- **Conventions.** Only the ones that differ from defaults and can't be read from the code:
  units, time, missing values, the tolerances that count as passing, and what is
  read-only.
- **Done means.** The rules that stop an agent from declaring success too early. They come
  from the framework's patterns:
  [Refuse to call complete](https://vweeks.github.io/scientific-agentic-engineering/framework/patterns/#refuse-to-call-complete),
  [Prove the check can fail](https://vweeks.github.io/scientific-agentic-engineering/framework/patterns/#prove-the-check-can-fail),
  and [Ask the real thing](https://vweeks.github.io/scientific-agentic-engineering/framework/patterns/#ask-the-real-thing).
- **Plans and decisions.** The plan comes before the code and is committed with it
  ([Plan before code](https://vweeks.github.io/scientific-agentic-engineering/framework/patterns/#plan-before-code),
  [Keep the decision trail](https://vweeks.github.io/scientific-agentic-engineering/framework/patterns/#keep-the-decision-trail)).
- **Review.** A reviewer that sees the claim and its evidence but not the conversation that
  produced them
  ([Fresh-eyes critique](https://vweeks.github.io/scientific-agentic-engineering/framework/patterns/#fresh-eyes-critique)).
  This repository's [Cynicχl](../agents/cynic-kyle/) is one such reviewer.
- **Gates.** The actions that always need a human decision, named before the work starts
  ([Decide the gates in advance](https://vweeks.github.io/scientific-agentic-engineering/framework/patterns/#decide-the-gates-in-advance)).

The framework's chapter on
[where guidance lives](https://vweeks.github.io/scientific-agentic-engineering/framework/structure/#where-guidance-lives)
covers what belongs in this file and what belongs elsewhere.

## What belongs somewhere else

- **Domain procedures**, such as how to check units or test conservation, belong in
  skills. A skill loads only when it is relevant, so it costs nothing in sessions that
  don't need it. See [`unit-check`](../skills/unit-check/).
- **Rules that must hold every time** belong in something enforced: a hook, a permission
  setting, a sandbox, or CI. The agent reads `AGENTS.md` as guidance, not as configuration,
  and a long session can lose track of it. State the gates here, and enforce the
  irreversible ones as well.
- **Rules for one part of the codebase** belong in your tool's path-scoped rules, or in an
  `AGENTS.md` inside that directory where your tool supports nested files.
- **Preferences about you rather than the project** (how cautious to be, how to report)
  belong in your user-level configuration, once, instead of in every repository.

## Which tools read it

Codex, Cursor, GitHub Copilot, and Claude Code all read `AGENTS.md` (checked October 2026).
Claude Code reads it when the project has no `CLAUDE.md` (version 2.1.277 or later). If you
also keep a `CLAUDE.md`, a line containing `@AGENTS.md` imports it, so both tools follow one
file. Gemini CLI reads `GEMINI.md` by default; add `AGENTS.md` to its `context.fileName`
setting to have it read this file instead. Tool support changes quickly; check your tool's
documentation.
