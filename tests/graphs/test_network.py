"""The Network pattern (Lab 53): peers hand work to each other with Command(goto=...)."""

from collections.abc import Callable
from unittest.mock import AsyncMock

from langchain_core.messages import AIMessage

from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.team.network import Handoff, build_network_graph, settle
from sovereign_brain.graphs.trail import stations
from sovereign_brain.services.portfolio import PortfolioService

CONTEXT = ResearchContext(portfolio=AsyncMock(spec=PortfolioService), analyst="amina")
TEAM_INPUT = {
    "client_id": "C-1042",
    "client_profile": "Amina Rahman Holdings, private-banking, risk profile moderate",
    "question": "Can this client live with a 40% fall in energy stocks?",
}
ONE_NOTE = {"notes": [{"author": "analyst", "text": "Energy is 18.5% of the portfolio."}]}


def hand_to(peer: str, call_id: str) -> AIMessage:
    args = {"to": peer, "reason": "Your part, please."}
    return AIMessage("", tool_calls=[{"name": "Handoff", "args": args, "id": call_id}])


def test_a_peer_never_hands_work_to_itself() -> None:
    settled = settle(Handoff(to="analyst", reason="Me again."), "analyst", ONE_NOTE, max_hops=6)

    assert settled.to == "risk_officer"


def test_no_writer_before_there_are_notes() -> None:
    settled = settle(Handoff(to="writer", reason="Done."), "risk_officer", {}, max_hops=6)

    assert settled.to == "analyst"


def test_at_the_hop_limit_the_writer_takes_over() -> None:
    state = {**ONE_NOTE, "turns": 5}

    settled = settle(Handoff(to="risk_officer", reason="More."), "analyst", state, max_hops=6)

    assert settled.to == "writer"


async def test_the_peers_hand_over_directly_and_the_writer_ends(make_model: Callable) -> None:
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

    result = await graph.ainvoke(
        TEAM_INPUT, context=CONTEXT, output_keys=["answer", "notes", "trail"]
    )

    assert stations(result["trail"]) == ["analyst", "risk_officer", "writer"]
    assert [note["author"] for note in result["notes"]] == ["analyst", "risk_officer"]
    assert result["answer"].startswith("No: a 40% energy fall")
