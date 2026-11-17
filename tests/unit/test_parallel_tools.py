"""Parallel tool calls (Lab 48): one reply, several tools, the time of the slowest."""

import asyncio
import time

from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode


@tool
async def slow_quote(ticker: str) -> str:
    """A price from a slow system."""
    await asyncio.sleep(0.5)
    return f"{ticker}: 62.40 USD"


def tool_station():
    """A ToolNode inside a one-station graph."""
    graph = StateGraph(MessagesState)
    graph.add_node("tools", ToolNode([slow_quote]))
    graph.add_edge(START, "tools")
    graph.add_edge("tools", END)
    return graph.compile()


async def test_three_tool_calls_take_the_time_of_one() -> None:
    calls = [
        {"name": "slow_quote", "args": {"ticker": ticker}, "id": f"call-{ticker}"}
        for ticker in ("GLFP", "SNRS", "MDNB")
    ]

    started = time.perf_counter()
    result = await tool_station().ainvoke({"messages": [AIMessage("", tool_calls=calls)]})
    elapsed = time.perf_counter() - started

    assert elapsed < 1.0  # one after another would take at least 1.5 seconds
    # Every result is matched to its call, in the order the model asked
    assert [m.tool_call_id for m in result["messages"][1:]] == [
        "call-GLFP",
        "call-SNRS",
        "call-MDNB",
    ]
