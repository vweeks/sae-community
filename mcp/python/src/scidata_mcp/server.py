"""The scidata_mcp server: the protocol side, shared by every adapter.

It exposes all three MCP primitives:

- Tools (the model decides when to call them): scidata_list, scidata_describe, scidata_read.
- A resource (the application decides when to attach it): scidata://{dataset}/metadata.
- A prompt (the user picks it): check_before_analysis.

Run it over stdio (the default; your agent tool starts it) or Streamable HTTP (--http; you
start it and the agent connects by URL). With stdio, stdout carries the protocol, so
everything else goes to stderr.
"""

import argparse
import logging
import math
import os
import sys
from typing import Annotated
from urllib.parse import quote

import numpy as np
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ResourceNotFoundError, ToolError
from mcp.server.mcpserver.resources import FunctionResource
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from scidata_mcp import __version__
from scidata_mcp.adapter import Adapter, AdapterError, json_values
from scidata_mcp.adapters.netcdf import NetCDFAdapter
from scidata_mcp.models import DescribeResult, ListResult, ReadResult

ADAPTERS = {"netcdf": NetCDFAdapter}

LIST_DEFAULT, LIST_MAX = 20, 50
#: The most values one scidata_read returns. Larger selections are refused, not truncated,
#: so the agent never mistakes part of an array for all of it.
READ_MAX_VALUES = 1000
LOOPBACK = ("127.0.0.1", "localhost", "::1")

INSTRUCTIONS = """\
Read-only access to scientific datasets. Start with scidata_list, then scidata_describe
before reading any values: it reports each variable's units, dimensions, and time encoding
exactly as the data declares them. Read small selections with scidata_read. Every response
carries provenance; cite it when you report a value."""

log = logging.getLogger("scidata_mcp")


class IndexRange(BaseModel):
    start: Annotated[int, Field(ge=0, description="First index, counting from 0.")]
    stop: Annotated[int, Field(ge=1, description="One past the last index.")]


DatasetId = Annotated[str, Field(min_length=1, max_length=512, description="A dataset id from scidata_list.")]


def build_server(adapter: Adapter) -> MCPServer:
    mcp = MCPServer("scidata_mcp", version=__version__, instructions=INSTRUCTIONS)

    # Every tool only reads. These hints tell the client so; they don't make it true.
    # Read-only behavior is enforced by the adapter having no way to write.
    reads = ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=adapter.open_world,
    )

    @mcp.tool(title="List datasets", annotations=reads)
    def scidata_list(
        offset: Annotated[int, Field(ge=0, description="How many datasets to skip.")] = 0,
        limit: Annotated[int, Field(ge=1, le=LIST_MAX, description="How many to return.")] = LIST_DEFAULT,
    ) -> ListResult:
        """List the datasets this server can read, with their ids. Paginated: if has_more is
        true, call again with offset set to next_offset."""
        datasets = _call(adapter.list_datasets)
        page = datasets[offset : offset + limit]
        has_more = offset + len(page) < len(datasets)
        return ListResult(
            datasets=page,
            total=len(datasets),
            offset=offset,
            has_more=has_more,
            next_offset=offset + len(page) if has_more else None,
            provenance=adapter.provenance(None),
        )

    @mcp.tool(title="Describe a dataset", annotations=reads)
    def scidata_describe(dataset: DatasetId) -> DescribeResult:
        """Report a dataset's dimensions, variables, and attributes as declared: each
        variable's units, dimensions, shape, and (for time) calendar. Call this before
        reading values or assuming anything about units or time."""
        return _describe(adapter, dataset)

    @mcp.tool(title="Read values", annotations=reads)
    def scidata_read(
        dataset: DatasetId,
        variable: Annotated[
            str, Field(min_length=1, max_length=256, description="A variable name from scidata_describe.")
        ],
        selection: Annotated[
            dict[str, IndexRange] | None,
            Field(
                description='Index range per dimension, e.g. {"time": {"start": 0, "stop": 24}}. '
                "Dimensions left out are read in full."
            ),
        ] = None,
    ) -> ReadResult:
        """Read one variable's values over an index range per dimension, with the matching
        coordinate values and the declared units. Returns at most 1000 values; narrow the
        selection for larger variables. Missing values are null."""
        selection = selection or {}
        sizes = _call(adapter.shape, dataset, variable)
        bounds = _bounds(sizes, selection, dataset, variable)
        count = math.prod(stop - start for start, stop in bounds.values())
        if count > READ_MAX_VALUES:
            raise ToolError(
                f"That selection has {count} values; the limit is {READ_MAX_VALUES}. "
                f"Dimension sizes are {sizes}. Narrow the selection, for example "
                f"{_example_selection(sizes)}."
            )
        dims, units, values, coords = _call(adapter.read, dataset, variable, bounds)
        missing = np.isnan(values)
        return ReadResult(
            dataset=dataset,
            variable=variable,
            units=units,
            dims=dims,
            shape=list(values.shape),
            selection={d: [start, stop] for d, (start, stop) in bounds.items()},
            values=json_values(values),
            missing_count=int(missing.sum()),
            coordinates=coords,
            provenance=adapter.provenance(dataset),
        )

    # Resource template: any client can read scidata://<id>/metadata. Slashes in an id are
    # percent-encoded (%2F) in the URI.
    @mcp.resource(
        "scidata://{dataset}/metadata",
        title="Dataset metadata",
        description="The same report as scidata_describe, for the application to attach as context.",
        mime_type="application/json",
    )
    def dataset_metadata(dataset: str) -> str:
        try:
            return _describe(adapter, dataset).model_dump_json(indent=2)
        except ToolError as exc:
            raise ResourceNotFoundError(str(exc)) from exc

    # Concrete resources too, one per dataset at startup, because some clients list
    # resources but not templates. Restart the server to pick up new files.
    try:
        startup_datasets = adapter.list_datasets()
    except AdapterError as exc:
        log.warning("could not list datasets at startup: %s", exc)
        startup_datasets = []
    for summary in startup_datasets:
        mcp.add_resource(
            FunctionResource(
                uri=f"scidata://{quote(summary.id, safe='')}/metadata",
                name=f"{summary.id} metadata",
                description=summary.title,
                mime_type="application/json",
                fn=lambda dataset=summary.id: dataset_metadata(dataset),
            )
        )

    @mcp.prompt(title="Check before analysis")
    def check_before_analysis(
        dataset: Annotated[str, Field(description="A dataset id from scidata_list.")],
    ) -> str:
        """Report what a dataset declares (units, time encoding, missing values) before any
        computation uses it."""
        return (
            f"Before any analysis of the dataset {dataset!r}, call scidata_describe on it and "
            "report, for every variable you expect to use:\n"
            "1. its units exactly as declared, or that it has none;\n"
            "2. for time variables, the units string and the calendar;\n"
            "3. whether its values are packed, and how missing values are marked.\n"
            "List anything missing or ambiguous as an open question. If you already have a "
            "units-checking skill or tool, run it on each declared units string; if not, say "
            "the units are unchecked and don't look for one. Do not compute anything until I "
            "have seen this report."
        )

    return mcp


def _call(fn, *args):
    """Run an adapter call, turning its anticipated failures into a ToolError the model reads."""
    try:
        return fn(*args)
    except AdapterError as exc:
        raise ToolError(str(exc)) from exc


def _describe(adapter: Adapter, dataset: str) -> DescribeResult:
    dims, variables, attrs = _call(adapter.describe, dataset)
    return DescribeResult(
        dataset=dataset,
        dimensions=dims,
        variables=variables,
        global_attributes=attrs,
        provenance=adapter.provenance(dataset),
    )


def _bounds(sizes, selection, dataset, variable) -> dict[str, tuple[int, int]]:
    unknown = sorted(set(selection) - set(sizes))
    if unknown:
        raise ToolError(
            f"{variable!r} in {dataset!r} has no dimension {', '.join(map(repr, unknown))}. "
            f"Its dimensions are {list(sizes)}."
        )
    bounds = {}
    for dim, size in sizes.items():
        rng = selection.get(dim)
        start, stop = (0, size) if rng is None else (rng.start, rng.stop)
        if not start < stop <= size:
            raise ToolError(
                f"Range [{start}, {stop}) is outside dimension {dim!r}, which has {size} entries "
                f"(valid: 0 <= start < stop <= {size})."
            )
        bounds[dim] = (start, stop)
    return bounds


def _example_selection(sizes: dict[str, int]) -> str:
    # Keep the first dimension's first few entries and one entry of each of the rest.
    parts = []
    for i, dim in enumerate(sizes):
        stop = min(sizes[dim], 10) if i == 0 else 1
        parts.append(f'"{dim}": {{"start": 0, "stop": {stop}}}')
    return "{" + ", ".join(parts) + "}"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="scidata-mcp", description=__doc__.splitlines()[0])
    parser.add_argument(
        "--data-root",
        default=os.environ.get("SCIDATA_DATA_ROOT"),
        help="Directory of datasets to serve (or set SCIDATA_DATA_ROOT). Nothing outside it is readable.",
    )
    parser.add_argument("--adapter", choices=sorted(ADAPTERS), default="netcdf")
    parser.add_argument("--http", action="store_true", help="Serve Streamable HTTP instead of stdio.")
    parser.add_argument("--host", default="127.0.0.1", help="HTTP only. Loopback addresses only.")
    parser.add_argument("--port", type=int, default=8000, help="HTTP only.")
    args = parser.parse_args(argv)

    # stdout is the protocol channel under stdio: log to stderr only.
    logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(name)s: %(message)s")

    if not args.data_root:
        parser.error("--data-root (or SCIDATA_DATA_ROOT) is required")
    try:
        adapter = ADAPTERS[args.adapter](args.data_root)
    except ValueError as exc:
        parser.error(str(exc))
    server = build_server(adapter)

    if not args.http:
        server.run("stdio")
        return
    if args.host not in LOOPBACK:
        # This template has no authentication or TLS, so it serves this machine only.
        parser.error(f"--host must be one of {', '.join(LOOPBACK)}; see the README on remote servers")
    # On a loopback host the SDK checks Host and Origin headers (DNS-rebinding protection).
    # Stateless JSON responses: no sessions to keep, and each request stands alone.
    log.info("serving http://%s:%d/mcp", args.host, args.port)
    server.run("streamable-http", host=args.host, port=args.port, stateless_http=True, json_response=True)
