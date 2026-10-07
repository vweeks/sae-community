"""Start the server under test the way an agent tool would, and talk to it only through MCP.

Nothing here imports the server. Any implementation, in any language, passes or fails the
same tests. Configure it with environment variables:

    SCIDATA_SERVER      Command that starts the server (default: python -m scidata_mcp).
                        It must accept --data-root DIR, and --http --port N.
    SCIDATA_OPEN_WORLD  "true" if the adapter reaches outside the machine (default: false).
    SCIDATA_SHOW_LOGS   Set to show the server's stderr log.

Like an agent tool, the MCP client starts a stdio server with a minimal environment, not
yours. If your server needs a variable, put it in the command: env NAME=value server ...
"""

import hashlib
import os
import shlex
import shutil
import sys
from contextlib import asynccontextmanager, nullcontext
from pathlib import Path

import anyio
import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters, stdio_client

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "data"


def server_command() -> list[str]:
    return shlex.split(os.environ.get("SCIDATA_SERVER", f"{shlex.quote(sys.executable)} -m scidata_mcp"))


def expected_open_world() -> bool:
    return os.environ.get("SCIDATA_OPEN_WORLD", "false").lower() == "true"


@pytest.fixture
def data_root(tmp_path: Path) -> Path:
    """A private copy of the fixtures, so tests can check it is left untouched."""
    root = tmp_path / "data"
    shutil.copytree(FIXTURES, root)
    return root


@asynccontextmanager
async def connect(data_root: Path):
    command, *args = server_command()
    params = StdioServerParameters(command=command, args=[*args, "--data-root", str(data_root)])
    # The server's stderr log is discarded; set SCIDATA_SHOW_LOGS=1 to see it.
    show = os.environ.get("SCIDATA_SHOW_LOGS")
    with nullcontext(sys.stderr) if show else open(os.devnull, "w") as errlog:  # noqa: ASYNC230
        async with Client(stdio_client(params, errlog=errlog)) as client:
            yield client


@pytest.fixture
def run(data_root):
    """run(fn) calls `await fn(client)` against a freshly started server and returns its result."""

    def runner(fn):
        async def main():
            async with connect(data_root) as client:
                return await fn(client)

        return anyio.run(main)

    return runner


def tree_digest(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }
