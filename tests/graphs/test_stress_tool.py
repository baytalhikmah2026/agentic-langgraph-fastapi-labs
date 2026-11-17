"""The research graph runs the stress-test tool when the model asks for it (Lab 42)."""

from collections.abc import Callable
from unittest.mock import AsyncMock

from langchain_core.messages import AIMessage

from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.research import build_research_graph
from sovereign_brain.services.portfolio import PortfolioService

REQUEST = {
    "client_id": "C-1042",
    "client_profile": "Amina Rahman Holdings, private-banking, risk profile moderate",
    "question": "What would a 40% fall in energy stocks cost this portfolio?",
}
STRESS_CALL = AIMessage(
    "",
    tool_calls=[
        {
            "name": "stress_test",
            "args": {
                "client_id": "C-1042",
                "sector": "Energy",
                "sector_value_usd": 185000,
                "portfolio_value_usd": 1000000,
                "shock_percent": 40,
                "risk_profile": "moderate",
            },
            "id": "call-1",
        }
    ],
)
ANSWER = AIMessage(
    "A 40% fall would cost 74,000 USD, 7.4% of the portfolio, above the 5.0% limit."
)


async def test_the_stress_test_result_backs_the_answer(make_model: Callable) -> None:
    graph = build_research_graph(make_model([STRESS_CALL, ANSWER]))
    context = ResearchContext(portfolio=AsyncMock(spec=PortfolioService), analyst="amina")

    result = await graph.ainvoke(REQUEST, context=context, output_keys=["messages", "checked"])

    tool_result = result["messages"][-2]
    assert tool_result.type == "tool"
    assert '"verdict": "limit breached"' in tool_result.content
    assert result["checked"] is True
