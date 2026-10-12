# Cynicχl, the Cynical Agent Linter

Cynicχl (pronounced "Cynic Kyle") is a subagent that argues the other side.

An agent session tends to settle on one route early and build on it. Optimism, untested
assumptions, and conclusions broader than the evidence pile up, because nothing in the
session is trying to knock them down. Cynicχl is given one decision or claim and the
evidence behind it, and tries to break it. *Cynicism is a method, not a predetermined
conclusion:* when it can't find a material problem, it says so and lists what it tried.

## What it does

It looks for unjustified optimism, untested assumptions, unhandled failure modes,
conclusions stronger than the evidence, and settling on one route without checking a
plausible alternative. It reads the files the brief points to, and it can't change or run
anything.

Its report starts with one of two verdicts, "material problems found" or "I tried to break
this and couldn't find a material problem", then lists the attacks it tried. Each finding
says:

- whether it is material (it would change a decision or a result) or a note;
- whether the claim is wrong or only not shown;
- the evidence;
- the cheapest check that would settle it;
- for a finding about the route, a named alternative and when it wins.

It reports no style nits and at most three notes.

**What it sees.** Only the brief the calling agent writes, not the conversation. That agent
reached the conclusion, so Cynicχl treats the brief's framing as something to examine too.

**When to use it.** When choosing between approaches, before calling work complete, and
before writing up conclusions. Not on every step.

## What's here

| Path | What it is |
|---|---|
| `cynic-kyle.md` | The agent for Claude Code: frontmatter, then the prompt. |
| `cynic-kyle.toml` | The same agent for Codex. `developer_instructions` holds the same prompt. |
| [`demos/`](demos/) | Three briefs to try it on, with what a good review should catch. |

The two files must carry the same prompt. `tests/cynic-kyle/` at the repository root fails
if they drift, so make every edit in both.

## Install

Copy one file into the agent folder your tool reads. Project folders are shared with
everyone who works on the project. User folders apply to all your projects.

| Tool | File | Project | User |
|---|---|---|---|
| Claude Code | `cynic-kyle.md` | `.claude/agents/` | `~/.claude/agents/` |
| Codex | `cynic-kyle.toml` | `.codex/agents/` | `~/.codex/agents/` |

This repository's Claude Code plugin also includes it (see the
[top-level README](../../README.md)). Codex's documentation doesn't say whether plugins can
carry custom agents, so for Codex, copy the file.

Each tool says "read-only" its own way, and this is the one line that differs between the
two files:

- Claude Code: `tools: Read, Grep, Glob` allows only those tools.
- Codex: `sandbox_mode = "read-only"`.

## Use

Ask for it by name, with the decision or claim and where its evidence is:

- Claude Code: "Use the cynic-kyle subagent to review this plan before we run it", or
  `@agent-cynic-kyle`. Claude may also delegate to it on its own when the description fits.
- Codex: "Have cynic-kyle review this plan before we run it."

The model writes a different report each run, so the demos are for trying the agent out,
not tests with fixed answers.
