"""Tools from outside the project join the tool wall (Lab 44)."""

from collections.abc import Callable
from unittest.mock import AsyncMock

from langchain_core.messages import AIMessage
from langchain_core.tools import StructuredTool

from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.research import build_research_graph
from sovereign_brain.services.portfolio import PortfolioService

REQUEST = {
    "client_id": "C-1042",
    "client_profile": "Amina Rahman Holdings, private-banking, risk profile moderate",
    "question": "How does the portfolio's exposure compare with its risk limit?",
}


async def risk_limit(risk_profile: str) -> str:
    """The largest loss from one sector shock that a risk profile accepts."""
    return '{"risk_profile": "moderate", "max_loss_percent": 5.0}'


# Stands in for a tool discovered on an MCP server
MCP_LIKE_TOOL = StructuredTool.from_function(coroutine=risk_limit, name="risk_limit")
ASK = AIMessage(
    "", tool_calls=[{"name": "risk_limit", "args": {"risk_profile": "moderate"}, "id": "call-1"}]
)
ANSWER = AIMessage("A moderate profile accepts a loss of at most 5.0% from one sector shock.")


async def test_an_extra_tool_is_offered_and_run(make_model: Callable) -> None:
    graph = build_research_graph(make_model([ASK, ANSWER]), extra_tools=[MCP_LIKE_TOOL])
    context = ResearchContext(portfolio=AsyncMock(spec=PortfolioService), analyst="amina")

    result = await graph.ainvoke(REQUEST, context=context, output_keys=["messages", "checked"])

    assert result["messages"][3].name == "risk_limit"
    assert "max_loss_percent" in result["messages"][3].content
    assert result["checked"] is True
