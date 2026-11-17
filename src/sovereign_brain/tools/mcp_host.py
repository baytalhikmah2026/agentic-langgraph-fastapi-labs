"""The MCP host (Lab 44): the API starts our MCP servers and uses their tools as LangChain tools.

Each server is a separate process that speaks the Model Context Protocol over stdio. The
adapter library (langchain-mcp-adapters) discovers their tools at start-up, so the agent's tool
wall grows without changing the graph. Every MCP call is written to the audit log.
"""

import logging
import sys
import time
from collections.abc import Awaitable, Callable

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import MCPToolCallRequest, MCPToolCallResult
from langchain_mcp_adapters.sessions import Connection

from sovereign_brain.core.settings import Settings

logger = logging.getLogger("sovereign_brain.mcp")
audit = logging.getLogger("sovereign_brain.audit.mcp")

# The MCP servers the API can start: name -> the Python module that runs the server
MCP_SERVERS = {
    "desk": "sovereign_brain.mcp_servers.desk",
}


def server_connections(names: list[str]) -> dict[str, Connection]:
    """How to start each enabled server: this same Python, running the server's module."""
    unknown = set(names) - set(MCP_SERVERS)
    if unknown:
        raise ValueError(f"Unknown MCP servers: {', '.join(sorted(unknown))}")
    return {
        name: {"transport": "stdio", "command": sys.executable, "args": ["-m", MCP_SERVERS[name]]}
        for name in names
    }


async def audit_tool_call(
    request: MCPToolCallRequest,
    handler: Callable[[MCPToolCallRequest], Awaitable[MCPToolCallResult]],
) -> MCPToolCallResult:
    """One audit line per MCP call: server, tool, arguments, outcome and duration."""
    started = time.perf_counter()
    outcome = "failed"  # stays "failed" if the call raises
    try:
        result = await handler(request)
        outcome = "error" if getattr(result, "isError", False) else "ok"
        return result
    finally:
        duration = round((time.perf_counter() - started) * 1000)
        audit.info(
            "MCP call %s.%s args=%s outcome=%s duration_ms=%d",
            request.server_name,
            request.name,
            request.args,
            outcome,
            duration,
        )


async def load_mcp_tools(settings: Settings) -> list[BaseTool]:
    """Discover the tools of every enabled MCP server; none if they cannot be reached."""
    if not settings.mcp_servers:
        return []
    client = MultiServerMCPClient(
        server_connections(settings.mcp_servers), tool_interceptors=[audit_tool_call]
    )
    try:
        tools = await client.get_tools()
    except Exception as error:  # the desk still works with its own tools
        logger.warning("MCP tools not available: %r", error)
        return []
    logger.info("MCP tools ready: %s", ", ".join(tool.name for tool in tools))
    return tools
