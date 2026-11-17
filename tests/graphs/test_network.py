"""The Network pattern (Labs 53, 58): peers hand work over, a watchdog breaks gridlocks."""

from collections.abc import Callable
from unittest.mock import AsyncMock

from langchain_core.messages import AIMessage

from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.team.network import (
    Handoff,
    build_network_graph,
    notebook,
    roll_back,
    settle,
)
from sovereign_brain.graphs.trail import stations
from sovereign_brain.services.portfolio import PortfolioService

TEAM_INPUT = {
    "client_id": "C-1042",
    "client_profile": "Amina Rahman Holdings, private-banking, risk profile moderate",
    "question": "Can this client live with a 40% fall in energy stocks?",
}
ONE_NOTE = {"notes": [{"author": "analyst", "text": "Energy is 18.5% of the portfolio."}]}
KEYS = ["answer", "notes", "trail"]


def context(max_team_turns: int = 6) -> ResearchContext:
    portfolio = AsyncMock(spec=PortfolioService)
    return ResearchContext(portfolio=portfolio, analyst="amina", max_team_turns=max_team_turns)


def hand_to(peer: str, call_id: str) -> AIMessage:
    args = {"to": peer, "reason": "Your part, please."}
    return AIMessage("", tool_calls=[{"name": "Handoff", "args": args, "id": call_id}])


def test_a_peer_never_hands_work_to_itself() -> None:
    settled = settle(Handoff(to="analyst", reason="Me again."), "analyst", ONE_NOTE)

    assert settled.to == "risk_officer"


def test_no_writer_before_there_are_notes() -> None:
    settled = settle(Handoff(to="writer", reason="Done."), "risk_officer", {})

    assert settled.to == "analyst"


def test_the_notebook_appends_and_rolls_back() -> None:
    notes = [{"author": "analyst", "text": "A"}, {"author": "risk_officer", "text": "B"}]

    assert notebook(notes, [{"author": "analyst", "text": "C"}])[-1]["text"] == "C"
    assert notebook(notes, roll_back(1)) == notes[:1]


async def test_the_peers_hand_over_through_the_watchdog(make_model: Callable) -> None:
    model = make_model(
        [
            AIMessage("Energy is 185,000 USD, 18.5% of the portfolio."),  # the analyst
            hand_to("risk_officer", "h1"),
            AIMessage("A 40% fall costs 7.4% of the portfolio; the limit is 5%."),  # risk officer
            hand_to("writer", "h2"),
            AIMessage("No: a 40% energy fall would cost 7.4%, above the 5% limit."),  # writer
        ]
    )
    graph = build_network_graph(model)

    result = await graph.ainvoke(TEAM_INPUT, context=context(), output_keys=KEYS)

    assert stations(result["trail"]) == [
        "analyst", "watchdog", "risk_officer", "watchdog", "writer",
    ]
    assert [note["author"] for note in result["notes"]] == ["analyst", "risk_officer"]
    assert result["answer"].startswith("No: a 40% energy fall")


async def test_a_gridlock_is_broken_and_rolled_back(make_model: Callable) -> None:
    same = "Energy is 18.5% of the portfolio."
    model = make_model(
        [
            AIMessage(same), hand_to("risk_officer", "h1"),  # new information
            AIMessage(same), hand_to("analyst", "h2"),  # nothing new (1)
            AIMessage(same + " "), hand_to("risk_officer", "h3"),  # nothing new (2): gridlock
            AIMessage("Energy is 18.5% of C-1042's portfolio."),  # the writer
        ]
    )
    graph = build_network_graph(model)

    result = await graph.ainvoke(TEAM_INPUT, context=context(), output_keys=KEYS)

    assert len(result["notes"]) == 1  # rolled back to the last real progress
    assert result["trail"][-2]["note"].startswith("Gridlock: 2 handoffs")
    assert stations(result["trail"])[-1] == "writer"


async def test_when_the_ttl_runs_out_the_writer_takes_over(make_model: Callable) -> None:
    model = make_model(
        [
            AIMessage("Energy is 18.5% of the portfolio."), hand_to("risk_officer", "h1"),
            AIMessage("A 40% fall costs 7.4%."), hand_to("analyst", "h2"),
            AIMessage("A 40% energy fall would cost 7.4% of the portfolio."),  # the writer
        ]
    )
    graph = build_network_graph(model)

    result = await graph.ainvoke(TEAM_INPUT, context=context(max_team_turns=2), output_keys=KEYS)

    assert result["trail"][-2]["note"].startswith("TTL expired")
    assert stations(result["trail"])[-1] == "writer"
