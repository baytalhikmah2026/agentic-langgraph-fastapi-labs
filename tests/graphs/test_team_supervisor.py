"""The Supervisor pattern (Lab 51): an editor hands the steps to its workers."""

from collections.abc import Callable
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage

from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.team.supervisor import Delegation, build_team_graph, guard
from sovereign_brain.graphs.trail import stations
from sovereign_brain.services.portfolio import PortfolioService

REQUEST = {
    "client_id": "C-1042",
    "client_profile": "Amina Rahman Holdings, private-banking, risk profile moderate",
    "question": "How large is the energy exposure?",
}
CONTEXT = ResearchContext(portfolio=AsyncMock(spec=PortfolioService), analyst="amina")
EVERYTHING = ["answer", "notes", "trail"]


def delegate(next_worker: str, task: str, call_id: str) -> AIMessage:
    """How a fake model hands back the editor's structured decision."""
    args = {"next": next_worker, "task": task}
    return AIMessage("", tool_calls=[{"name": "Delegation", "args": args, "id": call_id}])


async def test_the_editor_hands_out_the_work(make_model: Callable) -> None:
    model = make_model(
        [
            delegate("analyst", "Find the energy share.", "d1"),
            AIMessage("Energy is 18.5% of the portfolio."),  # the analyst agent's note
            delegate("writer", "Answer the question.", "d2"),
            AIMessage("Energy makes up 18.5% of the portfolio."),  # the writer's answer
            delegate("finish", "Done.", "d3"),
        ]
    )

    result = await build_team_graph(model).ainvoke(
        REQUEST, context=CONTEXT, output_keys=EVERYTHING
    )

    assert stations(result["trail"]) == [
        "supervisor", "analyst", "supervisor", "writer", "supervisor",
    ]
    assert result["notes"] == [{"author": "analyst", "text": "Energy is 18.5% of the portfolio."}]
    assert result["answer"] == "Energy makes up 18.5% of the portfolio."


async def test_unreadable_decisions_fall_back_to_the_rules(make_model: Callable) -> None:
    model = make_model(
        [
            AIMessage("I think the analyst should go first."),  # not a Delegation
            AIMessage("Energy is 18.5% of the portfolio."),
            AIMessage("Now the writer, please."),
            AIMessage("Energy makes up 18.5% of the portfolio."),
            AIMessage("All done."),
        ]
    )

    result = await build_team_graph(model).ainvoke(
        REQUEST, context=CONTEXT, output_keys=EVERYTHING
    )

    notes = [e["note"] for e in result["trail"] if e["node"] == "supervisor"]
    assert notes == [
        "Next: analyst (rules): Collect the facts needed for the question.",
        "Next: writer (rules): Write the final answer from the notes.",
        "Next: finish (rules): Done.",
    ]
    assert result["answer"] == "Energy makes up 18.5% of the portfolio."


@pytest.mark.parametrize(
    ("decision", "state", "expected"),
    [
        ("writer", {}, "analyst"),  # no notes yet: research first
        ("finish", {"notes": [{"author": "analyst", "text": "x"}]}, "writer"),  # no answer yet
        ("analyst", {"notes": [{"author": "analyst", "text": "x"}], "turns": 5}, "writer"),
    ],
)
def test_the_guard_keeps_the_order_of_work(decision: str, state: dict, expected: str) -> None:
    checked = guard(Delegation(next=decision, task="..."), state, max_turns=6)

    assert checked.next == expected
