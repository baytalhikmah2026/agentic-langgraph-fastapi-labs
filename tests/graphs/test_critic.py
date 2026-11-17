"""The writer and its critic (Lab 55): rounds of drafts until approval, or a clear give-up."""

from collections.abc import Callable
from unittest.mock import AsyncMock

from langchain_core.messages import AIMessage

from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.team.critic import build_critic_graph
from sovereign_brain.services.portfolio import PortfolioService

CASE = {
    "case_id": "0f3c9a2e1b5d4e8f9a0c6b2d7e1f4a3c",
    "client_id": "C-1042",
    "question": "How large is the energy exposure?",
    "notes": [{"author": "analyst", "text": "Energy is 185,000 USD, 18.5% of the portfolio."}],
    "answer": "Energy is a modest 18.5% of the portfolio.",
}


def context(max_revisions: int = 2) -> ResearchContext:
    portfolio = AsyncMock(spec=PortfolioService)
    return ResearchContext(portfolio=portfolio, analyst="amina", max_revisions=max_revisions)


async def test_a_draft_is_revised_until_the_critic_approves(make_model: Callable) -> None:
    approve = {"verdict": "approve", "problems": []}
    model = make_model(
        [
            AIMessage("Energy is 18.5% of the portfolio."),  # round 1: the client ID is missing
            AIMessage("For C-1042, energy is 18.5% of the portfolio."),  # round 2
            AIMessage("", tool_calls=[{"name": "Critique", "args": approve, "id": "c1"}]),
        ]
    )
    graph = build_critic_graph(model)

    keys = ["draft", "verdict", "rounds", "history"]  # the history too, not just the output
    result = await graph.ainvoke({"case": CASE}, context=context(), output_keys=keys)

    assert (result["verdict"], result["rounds"]) == ("approve", 2)
    assert result["draft"] == "For C-1042, energy is 18.5% of the portfolio."
    critiques = [entry for entry in result["history"] if entry["step"] == "critique"]
    assert [(c["by"], c["verdict"]) for c in critiques] == [
        ("rules", "revise"),
        ("model", "approve"),
    ]


async def test_out_of_rounds_the_critic_gives_up_plainly(make_model: Callable) -> None:
    model = make_model(
        [AIMessage("Energy is 18.5% of the portfolio."), AIMessage("Energy is 18.5%.")]
    )
    graph = build_critic_graph(model)

    result = await graph.ainvoke({"case": CASE}, context=context(max_revisions=1))

    assert result == {"draft": "Energy is 18.5%.", "verdict": "gave_up", "rounds": 2}
