"""Lab 48: measure what parallel tool calls save, with three slow look-ups.

Run with: uv run python scripts/parallel_tools_demo.py
No services are needed. Each tool waits one second, like a slow system would.
"""

import asyncio
import time

from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode


@tool
async def positions(client_id: str) -> str:
    """The client's holdings (slow system)."""
    await asyncio.sleep(1)
    return "GLFP, SNRS, MDNB"


@tool
async def quote(ticker: str) -> str:
    """The latest price of one ticker (slow system)."""
    await asyncio.sleep(1)
    return f"{ticker}: 62.40 USD"


@tool
async def note(name: str) -> str:
    """One research note (slow system)."""
    await asyncio.sleep(1)
    return "Rating: hold."


CALLS = [
    {"name": "positions", "args": {"client_id": "C-1042"}, "id": "call-1"},
    {"name": "quote", "args": {"ticker": "GLFP"}, "id": "call-2"},
    {"name": "note", "args": {"name": "gulf-petroleum.md"}, "id": "call-3"},
]
TOOLS = {"positions": positions, "quote": quote, "note": note}


def tool_station(tools: list) -> object:
    """A one-station graph: a ToolNode runs inside a graph, like in our research graph."""
    graph = StateGraph(MessagesState)
    graph.add_node("tools", ToolNode(tools))
    graph.add_edge(START, "tools")
    graph.add_edge("tools", END)
    return graph.compile()


async def main() -> None:
    started = time.perf_counter()
    for call in CALLS:  # one after another, as a simple loop would do it
        await TOOLS[call["name"]].ainvoke(call["args"])
    sequential = time.perf_counter() - started

    started = time.perf_counter()
    # One model reply that asks for three tools: ToolNode runs them at the same time
    result = await tool_station(list(TOOLS.values())).ainvoke(
        {"messages": [AIMessage("", tool_calls=CALLS)]}
    )
    parallel = time.perf_counter() - started

    print(f"One after another: 3 tools in {sequential:.2f} s")
    print(f"In parallel:       3 tools in {parallel:.2f} s")
    print(f"Saved: {sequential - parallel:.2f} s ({100 * (1 - parallel / sequential):.0f}%)")
    print("Results, in the order the model asked:")
    for message in result["messages"][1:]:  # [0] is the model reply itself
        print(f"- {message.tool_call_id} {message.name}: {message.content}")


asyncio.run(main())
