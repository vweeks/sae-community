"""Checks that the plugin manifests agree with each other and with the files they point to.

The repository is one plugin described four times: a marketplace file and a plugin manifest
for Claude Code (.claude-plugin/), and the same pair for Codex (.agents/plugins/ and
.codex-plugin/). Neither tool reports a missing file until someone installs the plugin, so
these tests catch a renamed folder or a version bumped in one place only.
"""

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


CLAUDE_MARKET = load(".claude-plugin/marketplace.json")
CLAUDE_PLUGIN = load(".claude-plugin/plugin.json")
CODEX_MARKET = load(".agents/plugins/marketplace.json")
CODEX_PLUGIN = load(".codex-plugin/plugin.json")


def resolve(path: str) -> Path:
    assert path.startswith("./"), f"{path!r}: component paths must start with ./ in both tools"
    return ROOT / path


def test_names_and_versions_match():
    names = {
        CLAUDE_PLUGIN["name"],
        CODEX_PLUGIN["name"],
        *(p["name"] for p in CLAUDE_MARKET["plugins"]),
        *(p["name"] for p in CODEX_MARKET["plugins"]),
    }
    assert names == {"sae-community"}
    assert CLAUDE_PLUGIN["version"] == CODEX_PLUGIN["version"]


def test_marketplaces_point_at_the_repository_root():
    assert [p["source"] for p in CLAUDE_MARKET["plugins"]] == ["."]
    assert [p["source"]["path"] for p in CODEX_MARKET["plugins"]] == ["./"]


def test_claude_agents_exist_and_are_agents():
    # Listing agents replaces Claude Code's scan of agents/, which would otherwise load the
    # READMEs and demo briefs under agents/ as agents. `claude plugin validate` still scans
    # the folder and warns about them; a running session loads only the listed file.
    for path in CLAUDE_PLUGIN["agents"]:
        text = resolve(path).read_text(encoding="utf-8")
        assert text.startswith("---\nname: "), f"{path} has no agent frontmatter"


def test_skills_folder_holds_skills():
    skills = resolve(CODEX_PLUGIN["skills"])
    found = sorted(p.parent.name for p in skills.glob("*/SKILL.md"))
    assert found, f"no SKILL.md under {skills}"
    for name in found:
        assert (skills / name / "agents" / "openai.yaml").is_file(), f"{name} lacks agents/openai.yaml"


def test_mcp_server_paths_exist():
    claude_args = CLAUDE_PLUGIN["mcpServers"]["scidata"]["args"]
    directory = claude_args[claude_args.index("--directory") + 1]
    assert directory.startswith("${CLAUDE_PLUGIN_ROOT}/")
    assert (ROOT / directory.removeprefix("${CLAUDE_PLUGIN_ROOT}/") / "pyproject.toml").is_file()


def test_mcp_command_is_the_packages_entry_point():
    with open(ROOT / "mcp" / "python" / "pyproject.toml", "rb") as f:
        scripts = tomllib.load(f)["project"]["scripts"]
    claude_args = CLAUDE_PLUGIN["mcpServers"]["scidata"]["args"]
    assert claude_args[claude_args.index("--directory") + 2] in scripts


def test_codex_plugin_has_no_mcp_server():
    # The server needs a data directory, and a Codex plugin has no way to ask for one: an
    # environment variable set when you start codex doesn't reach the background server that
    # starts MCP servers. Codex users add the server to config.toml instead (mcp/README.md).
    assert "mcpServers" not in CODEX_PLUGIN
