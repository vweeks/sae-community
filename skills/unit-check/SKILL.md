---
name: unit-check
description: Checks the physical units that data declares before code converts, combines, or compares quantities. Use when writing or reviewing code that reads values with units (NetCDF or HDF5 attributes, CSV headers, JSON or API metadata), when converting between units, when a units attribute is missing or unfamiliar, or when a time variable is encoded as "<unit> since <date>".
license: MIT. See LICENSE.txt.
---

# unit-check

Every conversion rests on a premise about what units the data is in. If that premise came
from a variable name, a comment, or habit, the arithmetic will run and the result will be
wrong. Check what the data declares before you write code that depends on it.

## When to run it

- When you first read a data file or API response the code will use.
- Before writing a conversion, or combining quantities from different sources.
- When reviewing code that converts units without checking the declared units itself.

## How to run it

Run from this skill's directory, in an environment that has pint (and netCDF4 for `scan`).
If they are missing, `uv run` installs them from the script's header; otherwise ask the user
before installing anything.

```
python scripts/unit_check.py require "<declared>" "<expected>"
python scripts/unit_check.py scan <file.nc> [--expect VAR=UNITS ...] [--json]
```

- `require` compares one declared units string, from any source, with the units the code
  expects. Pass `""` when nothing was declared.
- `scan` reports every variable in a NetCDF file, subgroups included. `--expect` checks
  named variables against the units the code expects.
- From Python, `require_units(declared, expected)` raises `MissingUnits`,
  `UnparseableUnits`, `WrongDimension`, `WrongUnit`, or `MalformedTimeEncoding`.

Exit codes: 0 no findings, 1 findings, 2 usage error. A usage error includes expected units
that can't be parsed, which means the call is wrong, not the data.

## What to do with each result

- `ok`: proceed.
- `wrong-unit`: the dimension matches but the unit doesn't. Convert explicitly where the
  data enters the code, and name the conversion in your report.
- `missing`, `unparseable`, `wrong-dimension`, `time-malformed`: stop. Report the variable,
  what was declared, and what the code expects, then ask the user how to proceed.
  IMPORTANT: never guess the units and continue.
- `time-encoding`: the encoding is well formed, but nothing checks that the reference date
  or calendar is right for the code. If results depend on absolute times, say which ones
  you relied on.
- `skipped`: grid-mapping, flag, and text variables carry no physical units.

A clean result means the declarations parse and match what the code expects. It does not
show that the declarations are true or that the values are plausible.

## Reference

- [references/udunits.md](references/udunits.md): which spellings are accepted, and known
  limits.
- [references/cf-time.md](references/cf-time.md): how `<unit> since <date>` encodings are
  checked.
