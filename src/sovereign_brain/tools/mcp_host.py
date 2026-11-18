"""The MCP host (Lab 44): the API starts our MCP servers and uses their tools as LangChain tools.

Each server is a separate process that speaks the Model Context Protocol over stdio. The
adapter library (langchain-mcp-adapters) discovers their tools at start-up, so the agent's tool
wall grows without changing the graph. Every MCP call is written to the audit log.
Lab 46: a server can get its own environment variables; only "market" gets the API token.
Lab 71: every tool result is checked by the injection guard before the model reads it.
"""

import logging
import sys
import time
from collections.abc import Awaitable, Callable

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import MCPToolCallRequest, MCPToolCallResult
from langchain_mcp_adapters.sessions import Connection
from mcp.types import CallToolResult, TextContent

from sovereign_brain.core.settings import Settings
from sovereign_brain.observability.metrics import INJECTIONS_BLOCKED
from sovereign_brain.security.injection import QUARANTINED, injection_rules

logger = logging.getLogger("sovereign_brain.mcp")
audit = logging.getLogger("sovereign_brain.audit.mcp")

# The MCP servers the API can start: name -> the Python module that runs the server
MCP_SERVERS = {
    "desk": "sovereign_brain.mcp_servers.desk",
    "notes": "sovereign_brain.mcp_servers.notes",  # Lab 45
    "market": "sovereign_brain.mcp_servers.market",  # Lab 46
    "workspace": "sovereign_brain.mcp_servers.workspace",  # Lab 60: the agency only
}


def server_environment(name: str, settings: Settings) -> dict[str, str] | None:
    """Extra environment variables for one server (Lab 46): each gets only what it needs."""
    if name == "market":
        return {
            "SB_MARKET_API_URL": settings.market_api_url,
            "SB_MARKET_API_TOKEN": settings.market_api_token.get_secret_value(),
        }
    return None


def server_connections(
    names: list[str], settings: Settings | None = None
) -> dict[str, Connection]:
    """How to start each enabled server: this same Python, running the server's module."""
    unknown = set(names) - set(MCP_SERVERS)
    if unknown:
        raise ValueError(f"Unknown MCP servers: {', '.join(sorted(unknown))}")
    connections: dict[str, Connection] = {}
    for name in names:
        connection: Connection = {
            "transport": "stdio",
            "command": sys.executable,
            "args": ["-m", MCP_SERVERS[name]],
        }
        env = server_environment(name, settings) if settings else None
        if env:
            connection["env"] = env
        connections[name] = connection
    return connections


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


async def screen_tool_result(
    request: MCPToolCallRequest,
    handler: Callable[[MCPToolCallRequest], Awaitable[MCPToolCallResult]],
) -> MCPToolCallResult:
    """The tool wall's guard (Lab 71): a result that gives orders never reaches the model."""
    result = await handler(request)
    if not isinstance(result, CallToolResult):
        return result
    text = " ".join(block.text for block in result.content if isinstance(block, TextContent))
    rules = injection_rules(text)
    if not rules:
        return result
    INJECTIONS_BLOCKED.labels("tool_result").inc()
    logger.warning(
        "Injection guard quarantined %s.%s: %s", request.server_name, request.name, rules
    )
    return CallToolResult(content=[TextContent(type="text", text=QUARANTINED)])


async def load_mcp_tools(settings: Settings, names: list[str] | None = None) -> list[BaseTool]:
    """Discover the tools of the given MCP servers (default: SB_MCP_SERVERS); none if unreachable.

    Lab 60: a team can get its own servers (the agency's workspace), apart from the tool wall.
    """
    names = settings.mcp_servers if names is None else names
    if not names:
        return []
    client = MultiServerMCPClient(
        server_connections(names, settings),
        tool_interceptors=[audit_tool_call, screen_tool_result],  # guard added in Lab 71
    )
    try:
        tools = await client.get_tools()
    except Exception as error:  # the desk still works with its own tools
        logger.warning("MCP tools not available: %r", error)
        return []
    logger.info("MCP tools ready: %s", ", ".join(tool.name for tool in tools))
    return tools
