"""Lab 43: watch the research graph recover from a tool error, with a scripted model.

Run with: uv run python scripts/tool_error_demo.py
No services are needed. The scripted model first sends an impossible 400% fall, reads the
error, sends a correct form, and then answers with the calculator's figures.
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.research import build_research_graph
from sovereign_brain.services.portfolio import PortfolioService

FORM = {
    "client_id": "C-1042",
    "sector": "Energy",
    "sector_value_usd": 185000,
    "portfolio_value_usd": 1000000,
    "shock_percent": 40,
    "risk_profile": "moderate",
}
SCRIPT = [
    AIMessage("", tool_calls=[{"name": "stress_test", "args": {**FORM, "shock_percent": 400},
                               "id": "call-1"}]),
    AIMessage("", tool_calls=[{"name": "stress_test", "args": FORM, "id": "call-2"}]),
    AIMessage("A 40% fall in energy would cost 74,000 USD, 7.4% of the portfolio, "
              "above the 5.0% limit for a moderate profile."),
]
REQUEST = {
    "client_id": "C-1042",
    "client_profile": "Amina Rahman Holdings, private-banking, risk profile moderate",
    "question": "What would a 40% fall in energy stocks cost this portfolio?",
}


class ScriptedModel(GenericFakeChatModel):
    """A model that gives the scripted replies in order and accepts any tools."""

    def bind_tools(self, tools: Any, **kwargs: Any) -> "ScriptedModel":
        return self


async def main() -> None:
    graph = build_research_graph(ScriptedModel(messages=iter(SCRIPT)))
    context = ResearchContext(portfolio=AsyncMock(spec=PortfolioService), analyst="amina")
    result = await graph.ainvoke(REQUEST, context=context, output_keys=["trail", "messages"])
    for entry in result["trail"]:
        print(f"{entry['node']:>8}  {entry['note']}")
    print(f"\nWhat the model read after its mistake:\n{result['messages'][3].content[:160]} ...")
    print(f"\nAnswer: {result['messages'][-1].content}")


asyncio.run(main())
