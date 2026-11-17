"""The research-notes MCP server (Lab 45), through a real MCP client session in memory."""

import json
from pathlib import Path

import pytest
from mcp.server.fastmcp import FastMCP
from mcp.shared.memory import create_connected_server_and_client_session

from sovereign_brain.mcp_servers.notes import create_server


@pytest.fixture
def notes(tmp_path: Path) -> Path:
    """A notes folder with one note."""
    root = tmp_path / "research_notes"
    root.mkdir()
    (root / "gulf-petroleum.md").write_text("# Gulf Petroleum\n\nRating: hold.\n", encoding="utf-8")
    return root


@pytest.fixture
def server(notes: Path, tmp_path: Path) -> FastMCP:
    return create_server(notes, tmp_path / "audit" / "notes_audit.jsonl")


async def test_notes_are_listed_and_read(server: FastMCP) -> None:
    async with create_connected_server_and_client_session(server) as session:
        listed = await session.call_tool("list_notes", {})
        read = await session.call_tool("read_note", {"name": "gulf-petroleum.md"})

    assert listed.structuredContent == {"result": ["gulf-petroleum.md"]}
    assert "Rating: hold." in read.content[0].text


async def test_a_saved_note_is_written_and_audited(
    server: FastMCP, notes: Path, tmp_path: Path
) -> None:
    async with create_connected_server_and_client_session(server) as session:
        result = await session.call_tool(
            "save_note", {"name": "medina-bank.md", "text": "# Medina Bank\n\nRating: buy.\n"}
        )

    assert result.isError is False
    assert (notes / "medina-bank.md").read_text(encoding="utf-8").startswith("# Medina Bank")
    lines = (tmp_path / "audit" / "notes_audit.jsonl").read_text(encoding="utf-8").splitlines()
    entry = json.loads(lines[-1])
    assert (entry["action"], entry["note"]) == ("create", "medina-bank.md")


async def test_a_path_outside_the_jail_is_a_tool_error(server: FastMCP) -> None:
    async with create_connected_server_and_client_session(server) as session:
        result = await session.call_tool("read_note", {"name": "../../secrets.md"})

    assert result.isError is True
    assert "outside the notes folder" in result.content[0].text
