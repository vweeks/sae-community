"""Tests for skills/unit-check/scripts/unit_check.py."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "skills" / "unit-check" / "scripts" / "unit_check.py"
_spec = importlib.util.spec_from_file_location("unit_check", SCRIPT)
uc = importlib.util.module_from_spec(_spec)
sys.modules["unit_check"] = uc  # dataclasses look the module up while it loads
_spec.loader.exec_module(uc)


def run_cli(*args):
    proc = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


# --- check / require_units -------------------------------------------------------------

@pytest.mark.parametrize("declared, expected", [
    ("m/s", "m/s"),
    ("m s-1", "m/s"),            # udunits shorthand
    ("kg m-2 s-1", "kg/m^2/s"),
    ("W m-2", "W/m**2"),
    ("m.s-1", "m/s"),            # udunits "." as multiplication
    ("hPa", "mbar"),             # different names, factor exactly 1
    ("Celsius", "degC"),         # udunits spelling
    ("°C", "degC"),
    ("degrees_north", "degree"), # CF coordinate units
    ("hours since 1970-01-01", "hours since 1970-01-01 00:00:00Z"),
])
def test_matching_units_pass(declared, expected):
    assert uc.check(declared, expected).status == "ok"
    uc.require_units(declared, expected)  # does not raise


@pytest.mark.parametrize("declared, expected, status, error", [
    (None, "K", "missing", uc.MissingUnits),
    ("   ", "K", "missing", uc.MissingUnits),
    ("furlongs per", "m", "unparseable", uc.UnparseableUnits),
    ("m", "s", "wrong-dimension", uc.WrongDimension),
    ("K", "hours since 1970-01-01", "wrong-dimension", uc.WrongDimension),
    ("hours since 1970-01-01", "K", "wrong-dimension", uc.WrongDimension),
    ("degC", "K", "wrong-unit", uc.WrongUnit),       # offset unit, same dimension
    ("km/h", "m/s", "wrong-unit", uc.WrongUnit),
    ("%", "1", "wrong-unit", uc.WrongUnit),          # both dimensionless, factor 0.01
    ("days since 1970-01-01", "hours since 1970-01-01", "wrong-unit", uc.WrongUnit),
    ("hours since 1980-01-01", "hours since 1970-01-01", "wrong-unit", uc.WrongUnit),
    ("hours since 1970-01-01 00:00 -06:00", "hours since 1970-01-01", "wrong-unit", uc.WrongUnit),
    ("months since 2000-01-01", "days since 2000-01-01", "time-malformed", uc.MalformedTimeEncoding),
    ("hours since yesterday", "hours since 1970-01-01", "time-malformed", uc.MalformedTimeEncoding),
    ("hours since 1970-13-01", "hours since 1970-01-01", "time-malformed", uc.MalformedTimeEncoding),
])
def test_each_failure_is_a_distinct_finding(declared, expected, status, error):
    result = uc.check(declared, expected)
    assert result.status == status
    assert result.is_finding
    with pytest.raises(error) as excinfo:
        uc.require_units(declared, expected)
    assert excinfo.value.result.status == status


def test_unparseable_expected_is_a_caller_error_not_a_finding():
    with pytest.raises(uc.ExpectedUnitsError):
        uc.check("K", "not_a_unit")


def test_describe_flags_reference_date_as_unverified():
    result = uc.describe("hours since 1900-01-01 00:00:00")
    assert result.status == "time-encoding"
    assert not result.is_finding
    assert "not verified" in result.message


# --- scan ---------------------------------------------------------------------------------

@pytest.fixture
def ncfile(tmp_path):
    netCDF4 = pytest.importorskip("netCDF4")
    path = tmp_path / "sample.nc"
    with netCDF4.Dataset(path, "w") as ds:
        ds.createDimension("time", 2)

        def var(name, units=None, group=ds):
            v = group.createVariable(name, "f4", ("time",))
            if units is not None:
                v.units = units

        var("time", "hours since 1970-01-01 00:00:00")
        ds["time"].calendar = "noleap"
        var("t2m", "K")
        var("wind", "m s-1")
        var("precip")                         # planted: no units
        var("rh", "%")
        var("odd", "furlongs per")            # planted: unparseable
        var("run_time", "months since 2000-01-01")  # planted: no fixed length
        ds.createVariable("crs", "i4", ()).grid_mapping_name = "latitude_longitude"
        flags = ds.createVariable("qc", "i1", ("time",))
        flags.flag_values = np.array([0, 1], dtype="i1")
        flags.flag_meanings = "good bad"
        obs = ds.createGroup("obs")
        obs.createDimension("time", 2)
        var("t", "degC", group=obs)
    return path


def by_name(results):
    return {r.variable: r for r in results}


def test_scan_reports_every_variable(ncfile):
    results = by_name(uc.scan(str(ncfile)))
    assert results["time"].status == "time-encoding"
    assert "noleap" in results["time"].message
    assert results["t2m"].status == "ok"
    assert results["wind"].status == "ok"
    assert results["rh"].status == "ok"
    assert results["precip"].status == "missing"
    assert results["odd"].status == "unparseable"
    assert results["run_time"].status == "time-malformed"
    assert results["crs"].status == "skipped"
    assert results["qc"].status == "skipped"
    assert results["obs/t"].status == "ok"


def test_scan_catches_planted_wrong_units(ncfile):
    """The code expects kelvin; the file's subgroup declares Celsius. The check must fail."""
    results = by_name(uc.scan(str(ncfile), {"t2m": "K", "obs/t": "K", "absent": "K"}))
    assert results["t2m"].status == "ok"
    assert results["obs/t"].status == "wrong-unit"
    assert results["absent"].status == "missing"


# --- CLI ----------------------------------------------------------------------------------

def test_cli_exit_codes():
    assert run_cli("require", "m s-1", "m/s")[0] == 0
    code, out, _ = run_cli("require", "degC", "K")
    assert code == 1 and out.startswith("wrong-unit")
    code, _, err = run_cli("require", "K", "not_a_unit")
    assert code == 2 and "cannot parse" in err


def test_cli_scan_json_and_bad_file(ncfile, tmp_path):
    code, out, _ = run_cli("scan", str(ncfile), "--expect", "obs/t=K", "--json")
    assert code == 1
    statuses = {r["variable"]: r["status"] for r in json.loads(out)}
    assert statuses["obs/t"] == "wrong-unit"
    assert run_cli("scan", str(tmp_path / "nope.nc"))[0] == 2
    assert run_cli("scan", str(ncfile), "--expect", "noequals")[0] == 2


def test_cli_scan_clean_file_exits_zero(tmp_path):
    netCDF4 = pytest.importorskip("netCDF4")
    path = tmp_path / "clean.nc"
    with netCDF4.Dataset(path, "w") as ds:
        ds.createDimension("x", 1)
        ds.createVariable("t2m", "f4", ("x",)).units = "K"
    assert run_cli("scan", str(path))[0] == 0
