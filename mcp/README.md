# scidata-mcp: a template MCP server for scientific data

Ask an agent what units a variable is in, how a file encodes time, or what a value is, and
it will often answer from memory or from what such files usually contain. The answer sounds
right. If the file says `degC` where the agent assumed kelvin, or counts days on a calendar
with no leap days, every later step inherits the mistake, and nothing in the session flags
it.

`scidata-mcp` is a starting point for giving the agent a way to ask the data instead. It is
a small, working MCP server you adapt to your own sources: read-only, bounded, with
provenance on every answer.

## Skill or MCP server?

Both extend what an agent can do, in different ways.

- A **skill** is a folder of instructions and scripts the agent reads when they're relevant.
  The agent runs the scripts itself, with its own permissions. This repository's
  [`unit-check`](../skills/unit-check/) is one.
- An **MCP server** is a separate program. Your agent tool starts it (or connects to it) and
  calls the operations it offers through the [Model Context Protocol](https://modelcontextprotocol.io).
  The agent can do only what the server exposes.

A server is worth writing when you need one of these:

- **Access the agent doesn't have:** data on another machine, behind an API, or in a format
  the agent's environment can't read.
- **Boundaries the agent shouldn't be trusted to keep:** read-only, one data directory, one
  set of hosts, no arbitrary code. A server enforces them in code, whatever the agent
  decides.
- **Provenance stamped by the server,** not remembered by the agent.

If none of these applies, a skill or a script is simpler and does the job.

## What the server offers

MCP defines three kinds of thing a server can offer. They differ in who decides when to use
them, and this template includes one or more of each:

| Kind | Who decides | Here |
|---|---|---|
| Tools | the model | `scidata_list`, `scidata_describe`, `scidata_read` |
| Resources | the application, or you | `scidata://{dataset}/metadata`: the describe report, to attach as context |
| Prompts | you | `check_before_analysis`: report what a dataset declares before any computation |

- `scidata_list` lists datasets, 20 at a time by default, with `has_more` and `next_offset`.
- `scidata_describe` reports dimensions, variables, and attributes as declared: each
  variable's units (or that it has none), calendar, packing, and fill value.
- `scidata_read` returns one variable over an index range per dimension, with the matching
  coordinates. It returns at most 1,000 values. A larger request is refused with an example
  of a narrower one, so the agent never mistakes part of an array for all of it. The limit
  is per read: an agent asked for everything can still read it in pieces.

Values come back as stored: packed values are unpacked, fill values become `null`, and
times are not decoded. Interpreting them stays visible to you, in the agent's own steps.

Each tool's error messages say what to try next (call `scidata_list` for the ids,
`scidata_describe` for the variables). Every response carries provenance: the source, a
SHA-256 of the file, the adapter, the server version, and when it was read.

**Client support varies.** Every MCP client supports tools. At the time of writing, Claude
Code offers resources as `@` mentions and prompts as `/` commands. Codex (0.160.1) lists
resources under `/mcp verbose` and lets the model list and read them when you ask, but it
doesn't offer MCP prompts at all. Check your tool's documentation.

## Try it

You need [uv](https://docs.astral.sh/uv/). The fixtures in `fixtures/data/` are three small
NetCDF files with things worth checking: Celsius beside kelvin, a `noleap` calendar, packed
values, fill values, units that need checking, and a variable with no units.

Use absolute paths in the commands below; the agent tool may start the server from a
different directory.

**Claude Code**, from your project:

```
claude mcp add --scope project scidata -- uv run --directory /path/to/sae-community/mcp/python scidata-mcp --data-root /path/to/sae-community/mcp/fixtures/data
```

This writes `.mcp.json` in your project. The next time you start Claude Code there, it
asks whether to use the new server; choose either "Use" option. `/mcp` should then show
`scidata` connected. Try:

- asking what calendar date the first time step in `model_grid.nc` is;
- typing `@scidata:` to attach a dataset's metadata. The list has one entry per dataset
  plus the template itself, and ids in subdirectories appear encoded (`profiles%2F...`);
- running the prompt, which the `/` menu shows as `/scidata:check_before_analysis` and
  tab completion writes as `/mcp__scidata__check_before_analysis station_obs.nc`.

**Codex**, in `~/.codex/config.toml` or a trusted project's `.codex/config.toml` (Codex
asks whether to trust a project the first time you start it there, and ignores the
project's config until you do):

```toml
[mcp_servers.scidata]
command = "uv"
args = ["run", "--directory", "/path/to/sae-community/mcp/python", "scidata-mcp",
        "--data-root", "/path/to/sae-community/mcp/fixtures/data"]
```

`/mcp verbose` should list the three tools and the resources. Ask the same question
about `model_grid.nc`, or ask Codex to list the scidata resources and read one.

Point `--data-root` at your own NetCDF directory when you're ready. The server reads files
ending in `.nc`, `.nc4`, or `.netcdf`, in subdirectories too, and nothing outside that
directory.

## Two ways to connect

- **stdio** (the default). Your agent tool starts the server as a child process and talks
  to it over standard input and output. Nothing listens on the network. Because stdout
  carries the protocol, the server logs only to stderr. This is the right choice when the
  data is on your machine.
- **Streamable HTTP** (`--http`). You start the server and it listens at
  `http://127.0.0.1:8000/mcp`; the agent tool connects by URL:

  ```
  uv run --directory /path/to/sae-community/mcp/python scidata-mcp --data-root /path/to/data --http
  claude mcp add --transport http scidata http://127.0.0.1:8000/mcp
  codex mcp add scidata --url http://127.0.0.1:8000/mcp
  ```

  The realistic use is a server running where the data lives, shared by several clients.
  This template binds to this machine only and refuses any other address. It rejects
  requests whose `Host` header isn't local, which blocks a web page from reaching it through
  DNS rebinding. It has no authentication and no TLS, so serving it to other machines safely
  is beyond a starter template.

## Make it yours

The server is split so that you change one part:

- **`server.py`** owns the protocol: the tools, the resource, the prompt, the limits, the
  error messages, and provenance. You shouldn't need to change it.
- **An adapter** answers three narrow questions about one kind of source: what datasets are
  there, what is in one, and what values are in a bounded selection. Implement
  [`adapter.py`](python/src/scidata_mcp/adapter.py) for your source (Zarr, HDF5, a database,
  an archive's API), register it in `ADAPTERS` in `server.py`, and run with
  `--adapter yourname`. [`adapters/netcdf.py`](python/src/scidata_mcp/adapters/netcdf.py) is
  the worked example.

Keep the [conventions](CONVENTIONS.md) when you do. Then rename the server and its tool
prefix for your project: tool names share a prefix (`scidata_`) so the agent can tell them
apart from other servers' tools.

## Check it

**Conformance.** [`conformance/`](conformance/) starts the server the way an agent tool
would and talks to it only through the protocol. It checks the five
[conventions](CONVENTIONS.md), pagination, error messages, all three kinds of offering, and
both transports. It never imports the server, so the same suite checks a server written in
any language, and it loops over every tool the server lists, so a tool you add can't skip
it.

```
cd python
uv run --group test pytest tests ../conformance
SCIDATA_SERVER="/path/to/your-server" uv run --group test pytest ../conformance
```

The second form runs the suite against a different server command, which must accept
`--data-root DIR` and `--http --port N`.

**Evaluation.** [`evals/scidata_eval.xml`](evals/scidata_eval.xml) holds ten questions about the
fixtures with fixed answers, several of them traps where the usual assumption is wrong. It
uses the evaluation format from Anthropic's
[`mcp-builder`](https://github.com/anthropics/skills/tree/main/skills/mcp-builder) skill, whose
harness runs a model against the server and scores its answers. A test in `python/tests`
checks that each answer can still be reached through the tools.

The [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector) is useful for
calling tools by hand. Start it with `npx @modelcontextprotocol/inspector`, choose the stdio
transport, and enter `uv` as the command with the same arguments as in the Claude Code
example above.

## What's here

| Path | What it is |
|---|---|
| [`python/`](python/) | The server in Python, with the NetCDF adapter and its tests. |
| [`CONVENTIONS.md`](CONVENTIONS.md) | The five rules, and how each is tested. |
| [`conformance/`](conformance/) | Protocol-level tests for any implementation. |
| [`evals/`](evals/) | Ten evaluation questions with fixed answers. |
| [`fixtures/`](fixtures/) | The sample datasets and the script that writes them. |

An Open-Meteo adapter (a public weather API, so `openWorldHint` true and a host allowlist)
and a TypeScript version of the server are planned for the 1.0.0 release.

## Out of scope

The server reports what a source declares; it doesn't check or convert units (the
`unit-check` skill does that, and neither depends on the other), decode times, compute
statistics, or write anything. It is a template to adapt, not a maintained service.
