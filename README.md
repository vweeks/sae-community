# SAE Community Repository

A curated starter set of templates and examples for developing scientific software with AI
coding agents: a skill, an MCP server template, a subagent, and a project instruction file.
Each one is meant to be copied into your own project and adapted. They put into practice
the [Scientific Agentic Engineering framework](https://vweeks.github.io/scientific-agentic-engineering/framework/),
and [`catalog.md`](catalog.md) maps each one to the patterns behind it.

Every artifact uses an open format: [Agent Skills](https://agentskills.io) for the skills,
the [Model Context Protocol](https://modelcontextprotocol.io) for the server, `AGENTS.md`
for the instruction file, and plain Markdown for the subagent's prompt. You can use them
with any AI coding tool that supports those formats. The repository was tested with Claude
Code and Codex, and it includes plugins for those two.

No maintenance is promised; see [scope and end date](#scope-and-end-date).

## What's here

| Artifact | What it is | Failure it helps catch |
|---|---|---|
| [`unit-check`](skills/unit-check/) | Skill | Code that converts or combines quantities using units it assumed instead of the units the data declares. |
| [`scidata-mcp`](mcp/) | MCP server template (Python) | An agent answering from memory about what a dataset contains. |
| [Cynicχl](agents/cynic-kyle/) (`cynic-kyle`) | Subagent, also packaged as a skill | A plan or result accepted because nothing in the session tried to break it. |
| [`AGENTS.md` template](agents-md/) | Project instruction file | An agent filling gaps in your project's standing rules with plausible defaults. |

Each folder's README starts with the failure in more detail, then covers how to use it.
[`CONTRIBUTING.md`](CONTRIBUTING.md) covers adapting each one to your project.

## Terms

These words get used loosely. Here they mean:

- **Skill:** a folder of instructions (`SKILL.md`), plus any scripts and reference files,
  that the agent loads when a task calls for it. The agent runs the scripts itself, with
  its own permissions. The format is the [Agent Skills](https://agentskills.io)
  specification, which Claude Code and Codex both read.
- **MCP server:** a separate program that your agent tool starts or connects to, and calls
  through the [Model Context Protocol](https://modelcontextprotocol.io). The agent can do
  only what the server offers.
- **Subagent:** a role defined by a prompt and a set of allowed tools. The main agent hands
  it a task; it works in its own context and reports back. Codex calls these custom agents.
  Each tool has its own file format, so Cynicχl comes as two files with the same prompt.
- **Project instruction file:** `AGENTS.md` (or Claude Code's `CLAUDE.md`) at the root of
  your repository, which the agent reads at the start of every session.
- **Plugin:** a package that bundles any of the above for one tool, so you install them
  together. Claude Code and Codex each have their own plugin format.
- **Marketplace:** a catalog file listing plugins. You add a marketplace to your tool, then
  install plugins from it. This repository is a marketplace with one plugin in it.

## Install

There are two routes: copy the files you want, which works with any tool, or install the
plugin for Claude Code or Codex, which brings several at once.

### Copy what you want

| Artifact | Claude Code | Codex | Another tool |
|---|---|---|---|
| `unit-check` | copy `skills/unit-check/` to `.claude/skills/unit-check/` | copy `skills/unit-check/` to `.agents/skills/unit-check/` | copy the folder to your tool's skills folder; Cursor, GitHub Copilot, and Gemini CLI read `.agents/skills/` |
| Cynicχl | copy `agents/cynic-kyle/cynic-kyle.md` to `.claude/agents/` | copy `agents/cynic-kyle/cynic-kyle.toml` to `.codex/agents/` | make a subagent in your tool's format from [`references/prompt.md`](skills/cynic-kyle-review/references/prompt.md), or use the skill below |
| Cynicχl as a skill | copy `skills/cynic-kyle-review/` to `.claude/skills/cynic-kyle-review/` | copy `skills/cynic-kyle-review/` to `.agents/skills/cynic-kyle-review/` | copy the folder to your tool's skills folder |
| `scidata-mcp` | `claude mcp add`, as in [`mcp/README.md`](mcp/README.md#try-it) | an `[mcp_servers]` entry, as in [`mcp/README.md`](mcp/README.md#try-it) | add the same command in your tool's MCP settings |
| `AGENTS.md` | copy the template to your repository root, as in [`agents-md/README.md`](agents-md/README.md) | the same | the same, if your tool reads `AGENTS.md` |

The Claude Code and Codex paths above are project folders, shared with everyone who works
on the project. For user-level folders, which apply to all your projects, and for other
tools' locations, see your tool's documentation.

This is the route to take if you mean to adapt an artifact, which is what they are for.

### Plugins for Claude Code and Codex

The hidden folders at the top of the repository hold these plugins' files: `.claude-plugin/`
for Claude Code, and `.agents/plugins/` and `.codex-plugin/` for Codex. Each tool packages
plugins its own way, so for any other tool, use the copy route above. (GitHub Copilot's
documentation says its CLI and VS Code extension can also read Claude Code's plugin format;
this plugin hasn't been tested there.) The `AGENTS.md`
template isn't in either plugin, because it belongs in your repository, not your tool.

**Claude Code** (tested with 2.1.296). The plugin carries `unit-check`, Cynicχl as both an
agent and a skill, and `scidata-mcp`; the MCP server needs [uv](https://docs.astral.sh/uv/).

```
claude plugin marketplace add vweeks/sae-community
claude plugin install sae-community@sae-community
```

Inside a session, `/plugin marketplace add vweeks/sae-community` and
`/plugin install sae-community@sae-community` do the same. Claude Code asks for the
directory `scidata-mcp` may read. To give it on the command line instead, add
`--config data_root=/path/to/data` to the install command. Installed this way, names
carry the plugin's prefix, such as `sae-community:cynic-kyle`.

**Codex** (tested with the 0.162.1 CLI; [Codex's documentation](https://developers.openai.com/codex/plugins)
says the IDE extension doesn't support plugins):

```
codex plugin marketplace add vweeks/sae-community
codex plugin add sae-community@sae-community
```

Or run `/plugins` inside Codex. The Codex plugin carries `unit-check` and the `cynic-kyle-review`
skill, which runs Cynicχl without installing it as an agent; Codex plugins can't carry
agents, and the [Cynicχl README](agents/cynic-kyle/README.md#install) explains the
difference. It leaves out
`scidata-mcp`, because a Codex plugin has no way to ask you for the directory the server
should read; add it to `config.toml` as in [`mcp/README.md`](mcp/README.md#try-it).

## Tests

GitHub Actions runs these on every push and pull request:

- `tests/unit-check/`: the checker, including the wrong inputs it must reject.
- `tests/cynic-kyle/`: the Claude Code and Codex files carry the same prompt and stay
  read-only.
- `tests/plugins/`: the plugin and marketplace files for both tools agree with each
  other and with the files they point to.
- `mcp/python/tests/` and `mcp/conformance/`: the server, and the protocol-level suite that
  checks any implementation of it.

To run them yourself, from the repository root:

```
uv run --python 3.12 --with pytest --with pint --with netCDF4 --with numpy pytest tests/unit-check
uv run --python 3.12 --with pytest pytest tests/cynic-kyle tests/plugins
cd mcp/python && uv run --group test pytest tests ../conformance
```

## Scope and end date

This repository was built as part of a 2026 Better Scientific Software (BSSw) Fellowship.
It is a curated starter set: templates and examples that demonstrate practices, meant to
be copied and adapted. It is not a package registry or a software distribution platform.

It will be archived (made read-only) after the fellowship ends in April 2027, and no
maintenance is promised before or after that. [`CONTRIBUTING.md`](CONTRIBUTING.md) covers
adapting an artifact and reporting a problem.

## Citation

[`CITATION.cff`](CITATION.cff) has the citation details; GitHub's "Cite this repository"
button formats them. DOI: [10.5281/zenodo.23197744](https://doi.org/10.5281/zenodo.23197744).

## License

MIT. See [`LICENSE`](LICENSE).

## Acknowledgment

This work was supported by the Better Scientific Software Fellowship Program, a
collaborative effort of the U.S. Department of Energy (DOE), Office of Advanced Scientific
Research via ANL under Contract DE-AC02-06CH11357 and the National Nuclear Security
Administration Advanced Simulation and Computing Program via LLNL under Contract
DE-AC52-07NA27344; and by the National Science Foundation (NSF) via SHI under Grant No.
2435328.
