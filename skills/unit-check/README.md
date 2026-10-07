# unit-check

Code that converts or combines physical quantities rests on a premise: the units the data is
in. When that premise comes from a variable name, a comment, or habit instead of what the
data declares, the arithmetic runs and the result is wrong. Nothing downstream flags it,
because the code is doing exactly what it says. A coding agent is especially prone to this,
since it fills gaps with plausible defaults and rarely stops to ask.

`unit-check` makes the premise something you check. It compares the units the data declares
with the units the code expects and reports a distinct result for each way that can go
wrong: no units declared, units it can't parse, a different physical dimension, the same
dimension in a different unit (°C where K was expected), and a malformed time encoding.

## What's here

| Path | What it is |
|---|---|
| `SKILL.md` | The skill: when the agent should run the check and what it does with each result. |
| `scripts/unit_check.py` | The checker, a plain Python module and command-line tool. It works without any agent. |
| `references/` | Accepted spellings and how time encodings are checked. The agent reads these only when needed. |
| `agents/openai.yaml` | Codex-only display settings. Other tools ignore it. |

## Install the skill

You can install the skill directly, as below, or through this repository's plugin (see the
[top-level README](../../README.md)). Either way, the agent gets the same folder.

To install it directly, copy this folder, unchanged, into your agent tool's skills directory:

- Claude Code: `.claude/skills/unit-check/` in your project.
- Codex: `.agents/skills/unit-check/` in your project.

Other tools that read the [Agent Skills](https://agentskills.io) format have an equivalent
location; check your tool's documentation.

## Use the checker directly

The checker needs pint, and netCDF4 for `scan`. With [uv](https://docs.astral.sh/uv/), the
dependencies come from the script's header:

```
uv run scripts/unit_check.py require "m s-1" "m/s"
uv run scripts/unit_check.py require "degC" "K"
uv run scripts/unit_check.py scan data.nc --expect t2m=K
```

From Python, with `scripts/` on your import path:

```python
from unit_check import require_units, WrongUnit

try:
    require_units(ds["t2m"].attrs.get("units"), "K")
except WrongUnit as err:
    ...  # convert explicitly, or stop
```

Exit codes are 0 for no findings, 1 for findings, and 2 for a usage error.

## What it doesn't do

It reads declarations; it can't tell whether a declaration is true, and it doesn't judge
whether a value is physically plausible. It isn't a conversion library (pint already is
one). The tests are in `tests/unit-check/` at the repository root.
