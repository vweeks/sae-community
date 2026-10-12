"""Checks that the two Cynicχl files say the same thing.

cynic-kyle.md (Claude Code) and cynic-kyle.toml (Codex) carry one prompt in two formats.
An edit to one that misses the other would make the agent behave differently by tool, so
the prompt, name, and description must match, and both files must keep the agent read-only.
"""

import difflib
import tomllib
from pathlib import Path

AGENT = Path(__file__).resolve().parents[2] / "agents" / "cynic-kyle"
READ_ONLY_TOOLS = {"Read", "Grep", "Glob"}


def markdown_agent() -> tuple[dict[str, str], str]:
    text = (AGENT / "cynic-kyle.md").read_text(encoding="utf-8")
    _, front, body = text.split("---\n", 2)
    meta = dict(line.split(": ", 1) for line in front.strip().splitlines())
    return meta, body.strip() + "\n"


def codex_agent() -> dict:
    with open(AGENT / "cynic-kyle.toml", "rb") as f:
        return tomllib.load(f)


def test_prompts_are_identical():
    _, body = markdown_agent()
    instructions = codex_agent()["developer_instructions"].strip() + "\n"
    diff = "".join(
        difflib.unified_diff(
            body.splitlines(keepends=True),
            instructions.splitlines(keepends=True),
            "cynic-kyle.md",
            "cynic-kyle.toml",
        )
    )
    assert not diff, f"The prompts differ; make the same edit in both files:\n{diff}"


def test_name_and_description_match():
    meta, _ = markdown_agent()
    codex = codex_agent()
    assert meta["name"] == codex["name"] == "cynic-kyle"
    assert meta["description"] == codex["description"]


def test_both_versions_are_read_only():
    meta, _ = markdown_agent()
    tools = {t.strip() for t in meta["tools"].split(",")}
    assert tools <= READ_ONLY_TOOLS, f"cynic-kyle.md grants {tools - READ_ONLY_TOOLS}"
    assert codex_agent()["sandbox_mode"] == "read-only"
