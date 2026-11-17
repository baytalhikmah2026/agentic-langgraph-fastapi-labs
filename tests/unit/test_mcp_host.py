"""The MCP host (Lab 44): how servers are started, and the audit line for every call."""

import logging
import sys

import pytest
from langchain_mcp_adapters.interceptors import MCPToolCallRequest
from mcp.types import CallToolResult, TextContent

from sovereign_brain.tools.mcp_host import audit_tool_call, server_connections


def test_each_server_runs_as_a_python_module() -> None:
    assert server_connections(["desk"]) == {
        "desk": {
            "transport": "stdio",
            "command": sys.executable,
            "args": ["-m", "sovereign_brain.mcp_servers.desk"],
        }
    }


def test_an_unknown_server_name_is_refused() -> None:
    with pytest.raises(ValueError, match="Unknown MCP servers: weather"):
        server_connections(["desk", "weather"])


async def test_every_call_leaves_an_audit_line(caplog: pytest.LogCaptureFixture) -> None:
    request = MCPToolCallRequest(name="glossary", args={"term": "bond"}, server_name="desk")

    async def handler(request: MCPToolCallRequest) -> CallToolResult:
        return CallToolResult(content=[TextContent(type="text", text="A loan ...")])

    with caplog.at_level(logging.INFO, logger="sovereign_brain.audit.mcp"):
        await audit_tool_call(request, handler)

    [line] = caplog.messages
    assert line.startswith("MCP call desk.glossary args={'term': 'bond'} outcome=ok duration_ms=")
