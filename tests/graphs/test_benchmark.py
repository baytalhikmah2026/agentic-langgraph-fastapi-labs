"""Measuring a team shape (Lab 59): every model call inside the graph is counted."""

from collections.abc import Callable
from unittest.mock import AsyncMock

from langchain_core.messages import AIMessage

from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.team.network import build_network_graph
from sovereign_brain.services.benchmark import TopologyRun, measure
from sovereign_brain.services.portfolio import PortfolioService

CONTEXT = ResearchContext(portfolio=AsyncMock(spec=PortfolioService), analyst="benchmark")
TEAM_INPUT = {
    "client_id": "C-1042",
    "client_profile": "Amina Rahman Holdings, private-banking, risk profile moderate",
    "question": "How large is the energy exposure?",
}


async def test_measure_counts_the_calls_of_every_agent_inside(make_model: Callable) -> None:
    handoff = {"to": "writer", "reason": "The notes answer the question."}
    model = make_model(
        [
            AIMessage("Energy is 18.5% of the portfolio."),  # the analyst's agent
            AIMessage("", tool_calls=[{"name": "Handoff", "args": handoff, "id": "h1"}]),
            AIMessage("Energy is a modest 18.5% of the portfolio."),  # the writer
        ]
    )

    run = await measure(TopologyRun("network"), build_network_graph(model), TEAM_INPUT, CONTEXT)

    assert (run.calls, run.answers) == (3, 1)
    assert run.seconds > 0
