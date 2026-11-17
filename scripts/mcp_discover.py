"""Lab 44: start the enabled MCP servers, list their tools, and call one of them.

Run with: uv run python scripts/mcp_discover.py
No model and no Docker services are needed: the servers are started as small local processes.
"""

import asyncio

from sovereign_brain.core.logging import configure_logging
from sovereign_brain.core.settings import get_settings
from sovereign_brain.tools.mcp_host import load_mcp_tools


async def main() -> None:
    settings = get_settings()
    configure_logging("INFO")
    tools = await load_mcp_tools(settings)
    print(f"\nDiscovered {len(tools)} MCP tools:")
    for tool in tools:
        print(f"- {tool.name}: {tool.description}")
    by_name = {tool.name: tool for tool in tools}
    if "glossary" in by_name:
        content = await by_name["glossary"].ainvoke({"term": "exposure"})
        # MCP tools answer with a list of content blocks; here there is one text block
        text = " ".join(block["text"] for block in content if block.get("type") == "text")
        print(f"\nglossary('exposure') -> {text}")


asyncio.run(main())
