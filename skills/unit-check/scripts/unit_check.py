# /// script
# requires-python = ">=3.10"
# dependencies = ["pint>=0.24", "netCDF4>=1.6"]
# ///
"""Check declared physical units before code converts or combines quantities.

Dependencies: pint for every command; netCDF4 only for `scan`. Run it with
`python unit_check.py ...` in an environment that has them, or `uv run unit_check.py ...`,
which reads the dependency block above.

Commands:
  require DECLARED EXPECTED   compare one declared units string with the units the code expects
  scan FILE [--expect VAR=UNITS ...] [--json]
                              report the units status of every variable in a NetCDF file

Exit codes: 0 no findings, 1 findings, 2 usage error.

The checker reads what the data declares. It cannot tell whether a declaration is true, and
it does not judge whether a magnitude is physically plausible.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass

import pint

# Statuses that count as findings (exit code 1).
FINDINGS = frozenset(
    {"missing", "unparseable", "wrong-dimension", "wrong-unit", "time-malformed"}
)

_UREG = pint.UnitRegistry()
# CF and udunits spellings that pint does not define.
for _definition in (
    "degrees_north = degree = degree_north = degrees_N = degreesN = degree_N = degreeN",
    "degrees_east = degree = degree_east = degrees_E = degreesE = degree_E = degreeE",
):
    _UREG.define(_definition)
_UREG.define("@alias degree_Celsius = Celsius")

# One udunits token: a unit name with an optional integer exponent ("m", "s-1", "m2").
_UDUNITS_TOKEN = re.compile(r"^([A-Za-z_°%]+)(-?\d+)?$")

_TIME = re.compile(r"^\s*(?P<unit>\S+)\s+since\s+(?P<ref>.+?)\s*$", re.IGNORECASE)
_REFERENCE = re.compile(
    r"^(?P<y>-?\d{1,4})-(?P<mo>\d{1,2})-(?P<d>\d{1,2})"
    r"(?:[ T](?P<h>\d{1,2}):(?P<mi>\d{2})(?::(?P<s>\d{2})(?:\.\d+)?)?)?"
    r"\s*(?P<tz>Z|UTC|GMT|[+-]\d{1,2}(?::?\d{2})?)?$",
    re.IGNORECASE,
)
_FIXED_TIME_UNITS = {
    "day": "day", "days": "day", "d": "day",
    "hour": "hour", "hours": "hour", "hr": "hour", "hrs": "hour", "h": "hour",
    "minute": "minute", "minutes": "minute", "min": "minute", "mins": "minute",
    "second": "second", "seconds": "second", "sec": "second", "secs": "second", "s": "second",
    "millisecond": "millisecond", "milliseconds": "millisecond", "ms": "millisecond",
    "microsecond": "microsecond", "microseconds": "microsecond", "us": "microsecond",
}
_CALENDAR_TIME_UNITS = {"month", "months", "year", "years", "yr", "yrs", "common_year", "common_years"}


@dataclass(frozen=True)
class Result:
    """The outcome of one check. `status` is "ok", "time-encoding", "skipped", or a finding."""

    status: str
    message: str
    declared: str | None = None
    expected: str | None = None
    variable: str | None = None

    @property
    def is_finding(self) -> bool:
        return self.status in FINDINGS


class UnitsError(Exception):
    """Raised by `require_units` when the declared units are not the expected units."""

    def __init__(self, result: Result):
        super().__init__(result.message)
        self.result = result


class MissingUnits(UnitsError):
    pass


class UnparseableUnits(UnitsError):
    pass


class WrongDimension(UnitsError):
    pass


class WrongUnit(UnitsError):
    pass


class MalformedTimeEncoding(UnitsError):
    pass


_ERRORS = {
    "missing": MissingUnits,
    "unparseable": UnparseableUnits,
    "wrong-dimension": WrongDimension,
    "wrong-unit": WrongUnit,
    "time-malformed": MalformedTimeEncoding,
}


class ExpectedUnitsError(ValueError):
    """The expected units are themselves unparseable: a mistake in the calling code."""


def _from_udunits(text: str) -> str:
    """Rewrite udunits shorthand ("kg m-2 s-1") as pint syntax ("kg * m**-2 * s**-1")."""
    if any(op in text for op in ("*", "/", "^", "(", ")")):
        return text
    parts = re.split(r"[ .]+", text.strip())
    converted = []
    for part in parts:
        match = _UDUNITS_TOKEN.match(part)
        if not match:
            return text
        name, exponent = match.groups()
        converted.append(f"{name}**{exponent}" if exponent else name)
    return " * ".join(converted)


def parse_units(text: str) -> pint.Unit:
    """Parse a units string in pint or udunits syntax. Raises ValueError if it can't."""
    try:
        return _UREG.Unit(_from_udunits(text))
    except Exception as exc:  # pint raises several unrelated types for bad input
        raise ValueError(f"cannot parse units {text!r}: {exc}") from None


def _is_offset(unit: pint.Unit) -> bool:
    return not _UREG.Quantity(1, unit)._is_multiplicative


def _same_unit(a: pint.Unit, b: pint.Unit) -> bool:
    """True if a and b are the same unit, including aliases with a factor of exactly 1."""
    if a == b:
        return True
    if _is_offset(a) or _is_offset(b):
        return False
    factor = _UREG.Quantity(1, a).to(b).magnitude
    return abs(factor - 1.0) < 1e-12


def _parse_time_encoding(text: str):
    """Return (unit, reference) for a CF time encoding, or raise ValueError with the reason."""
    match = _TIME.match(text)
    if not match:
        raise ValueError("not of the form '<unit> since <reference date>'")
    unit_name, reference = match.group("unit"), match.group("ref")
    if unit_name.lower() in _CALENDAR_TIME_UNITS:
        raise ValueError(
            f"'{unit_name}' has no fixed length (calendar months and years vary); "
            "CF advises against it. Ask how the producer defined it"
        )
    unit = _FIXED_TIME_UNITS.get(unit_name.lower())
    if unit is None:
        raise ValueError(f"'{unit_name}' is not a time unit")
    ref = _REFERENCE.match(reference)
    if not ref:
        raise ValueError(f"reference date {reference!r} is not a date like 1970-01-01 00:00:00")
    fields = {k: int(v) for k, v in ref.groupdict().items() if v is not None and k != "tz"}
    bounds = {"mo": (1, 12), "d": (1, 31), "h": (0, 23), "mi": (0, 59), "s": (0, 60)}
    for key, (low, high) in bounds.items():
        if key in fields and not low <= fields[key] <= high:
            raise ValueError(f"reference date {reference!r} has an out-of-range field")
    normalized = (
        fields["y"], fields["mo"], fields["d"],
        fields.get("h", 0), fields.get("mi", 0), fields.get("s", 0),
        (ref.group("tz") or "UTC").upper().replace("Z", "UTC").replace("GMT", "UTC"),
    )
    return unit, normalized, reference


def _is_time_encoding(text: str | None) -> bool:
    return bool(text) and " since " in f" {text.lower()} "


def check(declared: str | None, expected: str) -> Result:
    """Compare declared units with the units the code expects.

    Raises ExpectedUnitsError if `expected` can't be parsed, because that is a bug in the
    calling code, not a finding about the data.
    """
    if _is_time_encoding(expected):
        return _check_time(declared, expected)
    try:
        want = parse_units(expected)
    except ValueError as exc:
        raise ExpectedUnitsError(str(exc)) from None

    if declared is None or not declared.strip():
        return Result("missing", f"no units declared; expected {expected!r}. "
                      "Ask the data's producer or documentation; don't assume.",
                      declared, expected)
    if _is_time_encoding(declared):
        return Result("wrong-dimension", f"declared {declared!r} is a time encoding, "
                      f"but {expected!r} was expected", declared, expected)
    try:
        have = parse_units(declared)
    except ValueError:
        return Result("unparseable", f"declared units {declared!r} can't be parsed; expected "
                      f"{expected!r}. Find out what the producer meant before using the data.",
                      declared, expected)
    if have.dimensionality != want.dimensionality:
        return Result("wrong-dimension", f"declared {declared!r} is {have.dimensionality}, "
                      f"but {expected!r} is {want.dimensionality}: these are different "
                      "quantities, not a conversion", declared, expected)
    if not _same_unit(have, want):
        return Result("wrong-unit", f"declared {declared!r} has the expected dimension but is "
                      f"not {expected!r}; convert explicitly before use", declared, expected)
    return Result("ok", f"declared {declared!r} matches expected {expected!r}", declared, expected)


def _check_time(declared: str | None, expected: str) -> Result:
    try:
        want_unit, want_ref, _ = _parse_time_encoding(expected)
    except ValueError as exc:
        raise ExpectedUnitsError(f"expected time encoding {expected!r}: {exc}") from None
    if declared is None or not declared.strip():
        return Result("missing", f"no time encoding declared; expected {expected!r}",
                      declared, expected)
    if not _is_time_encoding(declared):
        return Result("wrong-dimension", f"declared {declared!r} is not a time encoding, "
                      f"but {expected!r} was expected", declared, expected)
    try:
        have_unit, have_ref, _ = _parse_time_encoding(declared)
    except ValueError as exc:
        return Result("time-malformed", f"declared {declared!r}: {exc}", declared, expected)
    if have_unit != want_unit:
        return Result("wrong-unit", f"declared {declared!r} counts in {have_unit}s, "
                      f"expected {want_unit}s", declared, expected)
    if have_ref != want_ref:
        return Result("wrong-unit", f"declared {declared!r} has a different reference date "
                      f"or zone than {expected!r}", declared, expected)
    return Result("ok", f"declared {declared!r} matches expected {expected!r}", declared, expected)


def describe(declared: str | None) -> Result:
    """Report the status of declared units when no particular unit is expected."""
    if declared is None or not declared.strip():
        return Result("missing", "no units declared. Ask the data's producer or documentation; "
                      "don't assume.", declared)
    if _is_time_encoding(declared):
        try:
            unit, _, reference = _parse_time_encoding(declared)
        except ValueError as exc:
            return Result("time-malformed", f"declared {declared!r}: {exc}", declared)
        return Result("time-encoding", f"well-formed: {unit}s since {reference}. The reference "
                      "date is declared, not verified; confirm it matches the source.", declared)
    try:
        unit = parse_units(declared)
    except ValueError:
        return Result("unparseable", f"declared units {declared!r} can't be parsed. Find out "
                      "what the producer meant before using the data.", declared)
    return Result("ok", f"parses as {unit:~} ({unit.dimensionality})", declared)


def require_units(declared: str | None, expected: str) -> Result:
    """Like `check`, but raise a UnitsError subclass on any finding."""
    result = check(declared, expected)
    if result.is_finding:
        raise _ERRORS[result.status](result)
    return result


def _skip_reason(var) -> str | None:
    attrs = set(var.ncattrs())
    if "grid_mapping_name" in attrs:
        return "grid-mapping variable"
    if attrs & {"flag_values", "flag_masks"}:
        return "flag variable"
    if var.dtype is str or getattr(var.dtype, "kind", "") in ("S", "U"):
        return "text variable"
    return None


def _walk(group, prefix=""):
    for name, var in group.variables.items():
        yield f"{prefix}{name}", var
    for name, sub in group.groups.items():
        yield from _walk(sub, f"{prefix}{name}/")


def scan(path: str, expect: dict[str, str] | None = None) -> list[Result]:
    """Report the units status of every variable in a NetCDF file, including subgroups.

    `expect` maps variable names (with "group/" prefixes for subgroups) to the units the code
    expects; those variables are checked against them.
    """
    try:
        import netCDF4
    except ImportError:
        raise RuntimeError("scan needs the netCDF4 package; install it or use `uv run`") from None
    expect = dict(expect or {})
    results = []
    with netCDF4.Dataset(path, "r") as ds:
        for name, var in _walk(ds):
            raw = var.getncattr("units") if "units" in var.ncattrs() else None
            declared = raw.decode() if isinstance(raw, bytes) else (None if raw is None else str(raw))
            if name in expect:
                result = check(declared, expect.pop(name))
            elif (reason := _skip_reason(var)) is not None:
                result = Result("skipped", reason, declared)
            else:
                result = describe(declared)
            if result.status == "time-encoding" and "calendar" in var.ncattrs():
                calendar = var.getncattr("calendar")
                result = Result(result.status, f"{result.message} Calendar: {calendar!r}; "
                                "check that the code's date handling uses it.", declared)
            results.append(Result(result.status, result.message, result.declared,
                                  result.expected, name))
    for name, units in expect.items():
        results.append(Result("missing", f"no variable named {name!r} in the file",
                              None, units, name))
    return results


def _parse_expect(items: list[str]) -> dict[str, str]:
    expect = {}
    for item in items:
        name, sep, units = item.partition("=")
        if not sep or not name:
            raise ExpectedUnitsError(f"--expect takes VAR=UNITS, got {item!r}")
        expect[name] = units
    return expect


def _print(results: list[Result], as_json: bool) -> None:
    if as_json:
        print(json.dumps([asdict(r) for r in results], indent=2, ensure_ascii=False))
        return
    for r in results:
        label = f"{r.variable}: " if r.variable else ""
        print(f"{r.status:<16} {label}{r.message}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="unit_check", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p_req = sub.add_parser("require", help="compare declared units with expected units")
    p_req.add_argument("declared", help='declared units; pass "" if none were declared')
    p_req.add_argument("expected", help="units the code expects")
    p_req.add_argument("--json", action="store_true", help="print JSON")
    p_scan = sub.add_parser("scan", help="report units for every variable in a NetCDF file")
    p_scan.add_argument("file")
    p_scan.add_argument("--expect", action="append", default=[], metavar="VAR=UNITS",
                        help="check VAR against UNITS (repeatable)")
    p_scan.add_argument("--json", action="store_true", help="print JSON")
    args = parser.parse_args(argv)

    try:
        if args.command == "require":
            results = [check(args.declared, args.expected)]
        else:
            results = scan(args.file, _parse_expect(args.expect))
    except (ExpectedUnitsError, RuntimeError, OSError) as exc:
        print(f"unit_check: {exc}", file=sys.stderr)
        return 2
    _print(results, args.json)
    return 1 if any(r.is_finding for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
