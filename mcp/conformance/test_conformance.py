"""Conformance tests for the five conventions in ../CONVENTIONS.md, plus the template's own
promises (all three primitives, pagination, actionable errors, both transports).

Tests loop over every tool the server lists, so a tool added later is checked too.
"""

import hashlib
import json
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

import anyio
import pytest
from conftest import connect, expected_open_world, server_command, tree_digest
from mcp import Client, MCPError

# Input names that would let a caller hand the server something to run, fetch, or open.
OPEN_ENDED_INPUTS = {
    "command", "cmd", "code", "script", "shell", "exec", "eval", "expression",
    "url", "uri", "endpoint", "host", "path", "file", "filename", "filepath", "query", "sql",
}  # fmt: skip


async def exercise_every_tool(client) -> dict[str, list]:
    """Call every tool at least once with valid arguments; return the results by tool name."""
    results: dict[str, list] = {}
    listing = await client.call_tool("scidata_list", {})
    results["scidata_list"] = [listing]
    for ds in listing.structured_content["datasets"]:
        described = await client.call_tool("scidata_describe", {"dataset": ds["id"]})
        results.setdefault("scidata_describe", []).append(described)
        numeric = [
            v
            for v in described.structured_content["variables"]
            if re.match(r"(u?int|float)", v["dtype"]) and v["dims"]
        ]
        if numeric:
            var = numeric[0]
            selection = {d: {"start": 0, "stop": 1} for d in var["dims"]}
            read = await client.call_tool(
                "scidata_read", {"dataset": ds["id"], "variable": var["name"], "selection": selection}
            )
            results.setdefault("scidata_read", []).append(read)
    tools = (await client.list_tools()).tools
    missing = {t.name for t in tools} - set(results)
    assert not missing, f"exercise_every_tool doesn't call {missing}; add a valid call for each new tool"
    return results


# -- 1. Read-only by construction ------------------------------------------------------


def test_data_root_is_unchanged_after_every_tool_runs(run, data_root):
    before = tree_digest(data_root)
    run(exercise_every_tool)
    assert tree_digest(data_root) == before


# -- 2. Narrow questions, not shells ---------------------------------------------------


def _properties(schema):
    for name, prop in (schema.get("properties") or {}).items():
        yield name, prop
        yield from _properties(prop)
        for sub in (prop.get("additionalProperties"), prop.get("items")):
            if isinstance(sub, dict):
                yield from _properties(sub)
    for sub in (schema.get("$defs") or {}).values():
        yield from _properties(sub)


def test_no_tool_takes_a_command_code_url_or_path(run):
    tools = run(lambda c: c.list_tools()).tools
    for tool in tools:
        for name, _ in _properties(tool.input_schema):
            assert name.lower() not in OPEN_ENDED_INPUTS, f"{tool.name} takes {name!r}"


def test_every_string_input_is_bounded(run):
    tools = run(lambda c: c.list_tools()).tools
    for tool in tools:
        for name, prop in _properties(tool.input_schema):
            if prop.get("type") == "string":
                assert "maxLength" in prop or "enum" in prop, f"{tool.name}.{name} is an unbounded string"


# -- 3. Provenance on every response ---------------------------------------------------


def test_every_tool_declares_provenance_in_its_output_schema(run):
    tools = run(lambda c: c.list_tools()).tools
    for tool in tools:
        assert tool.output_schema, f"{tool.name} has no output schema"
        assert "provenance" in tool.output_schema.get("required", []), f"{tool.name} omits provenance"


def test_every_response_carries_complete_provenance(run, data_root):
    results = run(exercise_every_tool)
    for name, calls in results.items():
        for result in calls:
            assert not result.is_error, f"{name}: {result.content[0].text}"
            prov = result.structured_content["provenance"]
            for field in ("source", "adapter", "server", "retrieved_at"):
                assert prov.get(field), f"{name} provenance lacks {field}"
            assert datetime.fromisoformat(prov["retrieved_at"]).utcoffset() is not None
            if not expected_open_world() and name != "scidata_list":
                file = data_root / prov["source"]
                assert prov["sha256"] == hashlib.sha256(file.read_bytes()).hexdigest()


# -- 4. Annotations declared and accurate ----------------------------------------------


def test_every_tool_declares_accurate_annotations(run):
    tools = run(lambda c: c.list_tools()).tools
    assert tools
    for tool in tools:
        a = tool.annotations
        assert a is not None, f"{tool.name} has no annotations"
        assert a.read_only_hint is True, tool.name
        assert a.destructive_hint is False, tool.name
        assert a.idempotent_hint is True, tool.name
        assert a.open_world_hint is expected_open_world(), tool.name


# -- 5. Confined -----------------------------------------------------------------------


@pytest.fixture
def outside_file(tmp_path, data_root):
    """A real NetCDF file next to the data root, not inside it."""
    target = tmp_path / "outside.nc"
    target.write_bytes(next(data_root.glob("*.nc")).read_bytes())
    return target


def test_ids_naming_files_outside_the_root_are_refused(run, outside_file):
    for dataset in ("../outside.nc", str(outside_file), "/etc/hosts", "station_obs.nc/../../outside.nc"):
        result = run(lambda c, d=dataset: c.call_tool("scidata_describe", {"dataset": d}))
        assert result.is_error, dataset
        assert "scidata_list" in result.content[0].text


def test_symlink_out_of_the_root_is_not_served(run, data_root, outside_file):
    (data_root / "escape.nc").symlink_to(outside_file)
    listing = run(lambda c: c.call_tool("scidata_list", {"limit": 50}))
    assert "escape.nc" not in [d["id"] for d in listing.structured_content["datasets"]]
    result = run(lambda c: c.call_tool("scidata_describe", {"dataset": "escape.nc"}))
    assert result.is_error


def test_resource_uri_cannot_reach_outside_the_root(run, outside_file):
    async def read(client):
        with pytest.raises(MCPError):
            await client.read_resource("scidata://..%2Foutside.nc/metadata")

    run(read)


# -- Pagination and limits --------------------------------------------------------------


def test_list_paginates_without_gaps_or_repeats(run):
    async def walk(client):
        seen, offset = [], 0
        while True:
            page = (await client.call_tool("scidata_list", {"offset": offset, "limit": 1})).structured_content
            seen += [d["id"] for d in page["datasets"]]
            if not page["has_more"]:
                return seen, page["total"]
            offset = page["next_offset"]

    seen, total = run(walk)
    assert len(seen) == total == len(set(seen)) > 1


def test_oversized_read_is_refused_with_a_way_forward(run):
    async def big(client):
        listing = await client.call_tool("scidata_list", {"limit": 50})
        for ds in listing.structured_content["datasets"]:
            described = await client.call_tool("scidata_describe", {"dataset": ds["id"]})
            for var in described.structured_content["variables"]:
                if var["shape"] and _product(var["shape"]) > 1000:
                    return await client.call_tool(
                        "scidata_read", {"dataset": ds["id"], "variable": var["name"]}
                    )
        pytest.skip("no variable in the fixtures exceeds the read limit")

    result = run(big)
    assert result.is_error
    assert "Narrow the selection" in result.content[0].text


def _product(shape):
    n = 1
    for s in shape:
        n *= s
    return n


# -- Errors tell the agent what to do next ---------------------------------------------


def test_unknown_variable_points_to_describe(run):
    async def bad(client):
        ds = (await client.call_tool("scidata_list", {})).structured_content["datasets"][0]["id"]
        return await client.call_tool("scidata_read", {"dataset": ds, "variable": "no_such_variable"})

    result = run(bad)
    assert result.is_error
    assert "scidata_describe" in result.content[0].text


# -- All three primitives --------------------------------------------------------------


def test_metadata_resource_matches_describe(run):
    async def both(client):
        templates = (await client.list_resource_templates()).resource_templates
        assert "scidata://{dataset}/metadata" in [t.uri_template for t in templates]
        ds = (await client.call_tool("scidata_list", {})).structured_content["datasets"][0]["id"]
        described = await client.call_tool("scidata_describe", {"dataset": ds})
        resource = await client.read_resource(f"scidata://{ds.replace('/', '%2F')}/metadata")
        return described.structured_content, resource.contents[0].text

    described, text = run(both)
    from_resource = json.loads(text)
    assert from_resource["variables"] == described["variables"]
    assert from_resource["provenance"]["sha256"] == described["provenance"]["sha256"]


def test_check_before_analysis_prompt(run):
    async def prompt(client):
        names = [p.name for p in (await client.list_prompts()).prompts]
        assert "check_before_analysis" in names
        return await client.get_prompt("check_before_analysis", {"dataset": "station_obs.nc"})

    text = run(prompt).messages[0].content.text
    assert "scidata_describe" in text and "station_obs.nc" in text


# -- Transports ------------------------------------------------------------------------


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def http_server(data_root):
    port = _free_port()
    proc = subprocess.Popen(
        [*server_command(), "--data-root", str(data_root), "--http", "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}/mcp"
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                break
        except OSError:
            time.sleep(0.1)
    else:
        proc.kill()
        pytest.fail("HTTP server did not start")
    yield url
    proc.terminate()
    proc.wait(timeout=10)


def test_streamable_http_serves_the_same_tools(http_server, run):
    async def over_http():
        async with Client(http_server) as client:
            return sorted(t.name for t in (await client.list_tools()).tools)

    assert anyio.run(over_http) == sorted(t.name for t in run(lambda c: c.list_tools()).tools)


def test_http_rejects_a_foreign_host_header(http_server):
    # A web page using DNS rebinding reaches localhost with its own hostname in Host.
    request = urllib.request.Request(
        http_server,
        data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode(),
        headers={
            "Host": "attacker.example",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    with pytest.raises(urllib.error.HTTPError) as refused:
        urllib.request.urlopen(request, timeout=10)
    assert refused.value.code in (400, 403, 421)


def test_http_refuses_to_bind_beyond_this_machine(data_root):
    proc = subprocess.run(
        [*server_command(), "--data-root", str(data_root), "--http", "--host", "0.0.0.0"],
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode != 0


def test_stdio_server_starts_from_the_configured_command(data_root):
    # The agent tool's own launch path: a command plus --data-root, nothing else.
    async def ping():
        async with connect(data_root) as client:
            return [t.name for t in (await client.list_tools()).tools]

    assert {"scidata_list", "scidata_describe", "scidata_read"} <= set(anyio.run(ping))


if __name__ == "__main__":
    sys.exit(pytest.main([str(Path(__file__).parent)]))
