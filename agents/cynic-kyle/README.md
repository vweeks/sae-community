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

The same prompt also ships as a skill,
[`skills/cynic-kyle-review/`](../../skills/cynic-kyle-review/), for tools that can't install
the agent (see below). All three copies must match: `tests/cynic-kyle/` at the repository
root fails if they drift, so make every edit in all three.

## Install

Copy one file into the agent folder your tool reads. Project folders are shared with
everyone who works on the project. User folders apply to all your projects.

| Tool | File | Project | User |
|---|---|---|---|
| Claude Code | `cynic-kyle.md` | `.claude/agents/` | `~/.claude/agents/` |
| Codex | `cynic-kyle.toml` | `.codex/agents/` | `~/.codex/agents/` |

This repository's Claude Code plugin also includes it (see the
[top-level README](../../README.md)). Installed that way, its name carries the plugin's
prefix: `sae-community:cynic-kyle`.

Codex plugins can't carry custom agents (checked in Codex 0.162.1), so the Codex plugin
gives you Cynicχl through the `cynic-kyle-review` skill instead. The skill hands the review
to a `cynic-kyle` agent when one is installed. Otherwise it starts a helper agent with the
same prompt and no conversation history. That helper runs with your session's permissions:
the prompt tells it to only read, but the tool doesn't enforce that. Copy the `.toml` if you
want read-only enforced. The skill is in the [Agent Skills](https://agentskills.io) format, so you can also copy its
folder into another tool. Its fresh-eyes guarantee depends on that tool starting a helper
agent without the conversation; when the tool can't, the skill gives you the prompt and
brief to paste into a new session instead.

Each tool says "read-only" its own way, and this is the one line that differs between the
two files:

- Claude Code: `tools: Read, Grep, Glob` allows only those tools.
- Codex: `sandbox_mode = "read-only"`.

## Use

Ask for it by name, with the decision or claim and where its evidence is:

- Claude Code: "Use the cynic-kyle subagent to review this plan before we run it", or
  `@agent-cynic-kyle`. Claude may also delegate to it on its own when the description fits.
- Codex: "Have cynic-kyle review this plan before we run it, starting it with no
  conversation history." Codex gives a helper agent a copy of the whole conversation
  unless told otherwise, and the review works only if the reviewer hasn't seen how the
  plan was reached. The `cynic-kyle-review` skill asks for this itself.

If you installed it through the Claude Code plugin, use `sae-community:cynic-kyle` in place
of `cynic-kyle`.

The model writes a different report each run, so the demos are for trying the agent out,
not tests with fixed answers.
