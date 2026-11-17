"""The project-workspace MCP server (Lab 60), through a real MCP client session in memory."""

import json
from pathlib import Path

import pytest
from mcp.server.fastmcp import FastMCP
from mcp.shared.memory import create_connected_server_and_client_session

from sovereign_brain.mcp_servers.workspace import create_server

CODE = "def weights(values):\n    return values\n"


@pytest.fixture
def audit_file(tmp_path: Path) -> Path:
    return tmp_path / "audit" / "workspace_audit.jsonl"


@pytest.fixture
def server(tmp_path: Path, audit_file: Path) -> FastMCP:
    return create_server(tmp_path / "workspace", audit_file)


async def test_a_file_is_written_listed_and_read(server: FastMCP) -> None:
    async with create_connected_server_and_client_session(server) as session:
        written = await session.call_tool("write_file", {"name": "weights.py", "text": CODE})
        listed = await session.call_tool("list_files", {})
        read = await session.call_tool("read_file", {"name": "weights.py"})

    assert written.isError is False
    assert listed.structuredContent == {"result": ["weights.py"]}
    assert read.content[0].text == CODE


async def test_names_outside_the_workspace_or_of_other_types_are_refused(
    server: FastMCP,
) -> None:
    async with create_connected_server_and_client_session(server) as session:
        escape = await session.call_tool("write_file", {"name": "../evil.py", "text": CODE})
        binary = await session.call_tool("write_file", {"name": "run.exe", "text": CODE})

    assert escape.isError is True
    assert binary.isError is True


async def test_every_write_is_audited(server: FastMCP, audit_file: Path) -> None:
    async with create_connected_server_and_client_session(server) as session:
        await session.call_tool("write_file", {"name": "weights.py", "text": CODE})
        await session.call_tool("write_file", {"name": "weights.py", "text": CODE + "\n"})

    lines = [json.loads(line) for line in audit_file.read_text(encoding="utf-8").splitlines()]
    assert [line["action"] for line in lines] == ["create", "update"]
