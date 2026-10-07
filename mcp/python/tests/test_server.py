"""Tests for the Python server and its NetCDF adapter, run in-process.

The language-independent checks live in ../../conformance. These cover what that suite
can't see from outside: how values are converted, and that every answer in the evaluation
file can still be reached through the tools.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

import anyio
import cftime
import pytest
from mcp import Client

from scidata_mcp.adapters.netcdf import NetCDFAdapter
from scidata_mcp.server import build_server

MCP_DIR = Path(__file__).resolve().parents[2]
FIXTURES = MCP_DIR / "fixtures" / "data"


def call(name: str, args: dict) -> dict:
    async def main():
        async with Client(build_server(NetCDFAdapter(FIXTURES))) as client:
            result = await client.call_tool(name, args)
            assert not result.is_error, result.content[0].text
            return result.structured_content

    return anyio.run(main)


def read(dataset, variable, **selection):
    sel = {dim: {"start": a, "stop": b} for dim, (a, b) in selection.items()}
    return call("scidata_read", {"dataset": dataset, "variable": variable, "selection": sel})


def variable(dataset, name):
    return next(v for v in call("scidata_describe", {"dataset": dataset})["variables"] if v["name"] == name)


# -- values are reported as stored ------------------------------------------------------


def test_float32_values_are_reported_as_their_shortest_decimal():
    assert read("station_obs.nc", "precip", time=(6, 9), station=(0, 1))["values"] == [[0.2], [1.4], [0.6]]


def test_fill_values_become_null_and_are_counted():
    result = read("station_obs.nc", "precip", station=(1, 2))
    assert [row[0] for row in result["values"]].count(None) == 3
    assert result["missing_count"] == 3
    assert variable("station_obs.nc", "precip")["fill_value"] == -999.0


def test_packed_values_are_unpacked_and_the_packing_is_declared():
    info = variable("model_grid.nc", "pr")
    assert (info["packed"], info["dtype"], info["scale_factor"]) == (True, "int16", 1e-6)
    value = read("model_grid.nc", "pr", time=(0, 1), lat=(2, 3), lon=(1, 2))["values"][0][0][0]
    assert value == pytest.approx(12e-6)


def test_times_are_returned_as_stored_not_decoded():
    result = read("model_grid.nc", "time", time=(0, 1))
    assert result["values"] == [9490.0]
    assert result["units"] == "days since 2000-01-01"


def test_units_are_reported_exactly_as_declared():
    assert variable("profiles/ocean_profile.nc", "temp")["units"] == "Celsius"
    assert variable("station_obs.nc", "rh")["units"] is None


# -- the evaluation answers are still reachable -----------------------------------------


def _answers() -> dict[str, str]:
    root = ET.parse(MCP_DIR / "evals" / "scidata_eval.xml").getroot()
    return {qa.findtext("question"): qa.findtext("answer") for qa in root.findall("qa_pair")}


def _derive() -> list[str]:
    """Answer each evaluation question, in order, using only the server's tools."""
    listing = call("scidata_list", {})["datasets"]
    noleap = [
        d["id"]
        for d in listing
        if any(v["calendar"] == "noleap" for v in call("scidata_describe", {"dataset": d["id"]})["variables"])
    ]

    stations = read("station_obs.nc", "station")["values"]
    s101, s102 = stations.index(101), stations.index(102)
    hours = read("station_obs.nc", "time")["values"]
    t2m = read(
        "station_obs.nc", "t2m", time=(hours.index(6.0), hours.index(6.0) + 1), station=(s102, s102 + 1)
    )
    precip = read("station_obs.nc", "precip")["values"]

    no_units = [
        v["name"]
        for v in call("scidata_describe", {"dataset": "station_obs.nc"})["variables"]
        if not v["is_coordinate"] and v["units"] is None
    ]

    time = variable("model_grid.nc", "time")
    first = read("model_grid.nc", "time", time=(0, 1))["values"][0]
    first_date = cftime.num2date(first, time["units"], time["calendar"])

    profile = read("profiles/ocean_profile.nc", "temp")
    depth = next(d for d, t in zip(profile["coordinates"]["depth"]["values"], profile["values"]) if t < 10)

    tas = read("model_grid.nc", "tas", time=(0, 1))
    grid = tas["values"][0]
    hottest = max((v, j) for row in grid for j, v in enumerate(row))[1]

    return [
        noleap[0],
        f"{t2m['values'][0][0]:.0f}",
        str([row[s102] for row in precip].count(None)),
        f"{sum(row[s101] for row in precip):.1f}",
        no_units[0],
        variable("model_grid.nc", "pr")["dtype"],
        first_date.strftime("%Y-%m-%d"),
        variable("profiles/ocean_profile.nc", "salinity")["units"],
        f"{depth:.0f}",
        f"{tas['coordinates']['lon']['values'][hottest]:.0f}",
    ]


def test_every_evaluation_answer_is_reachable_through_the_tools():
    expected = list(_answers().values())
    assert len(expected) == 10
    assert _derive() == expected
