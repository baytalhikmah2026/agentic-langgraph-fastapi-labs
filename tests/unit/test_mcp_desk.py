"""The desk-reference MCP server (Lab 44), tested through a real MCP client session in memory."""

from mcp.shared.memory import create_connected_server_and_client_session

from sovereign_brain.mcp_servers.desk import server


async def test_a_client_discovers_the_two_tools() -> None:
    async with create_connected_server_and_client_session(server) as session:
        listed = await session.list_tools()

    tools = {tool.name: tool for tool in listed.tools}
    assert set(tools) == {"risk_limit", "glossary"}
    assert "conservative" in str(tools["risk_limit"].inputSchema)


async def test_risk_limit_returns_structured_data() -> None:
    async with create_connected_server_and_client_session(server) as session:
        result = await session.call_tool("risk_limit", {"risk_profile": "moderate"})

    assert result.isError is False
    assert result.structuredContent == {"risk_profile": "moderate", "max_loss_percent": 5.0}


async def test_an_unknown_term_comes_back_as_a_tool_error() -> None:
    async with create_connected_server_and_client_session(server) as session:
        result = await session.call_tool("glossary", {"term": "unicorn"})

    assert result.isError is True
    assert "Known terms" in result.content[0].text
