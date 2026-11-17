"""Shared state across graphs (Lab 54): namespaces, the CaseFile bridge, the briefing graph."""

from collections.abc import Callable
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import ValidationError

from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.team.bridge import CaseFile, CaseNotFound, export_case
from sovereign_brain.graphs.team.briefing import build_briefing_graph
from sovereign_brain.graphs.team.network import build_network_graph
from sovereign_brain.memory.shared_state import case_thread
from sovereign_brain.services.portfolio import PortfolioService

CONTEXT = ResearchContext(portfolio=AsyncMock(spec=PortfolioService), analyst="amina")
CASE_ID = "0f3c9a2e1b5d4e8f9a0c6b2d7e1f4a3c"
TEAM_INPUT = {
    "client_id": "C-1042",
    "client_profile": "Amina Rahman Holdings, private-banking, risk profile moderate",
    "question": "How large is the energy exposure?",
}


def test_each_graph_and_analyst_has_its_own_namespace() -> None:
    threads = {
        case_thread("network", "amina", CASE_ID),
        case_thread("briefing", "amina", CASE_ID),
        case_thread("network", "omar", CASE_ID),
    }

    assert len(threads) == 3  # same case ID, three separate places


def test_the_bridge_turns_back_incomplete_or_unknown_fields() -> None:
    case = {**TEAM_INPUT, "case_id": CASE_ID, "notes": [{"author": "analyst", "text": "18.5%"}]}
    del case["client_profile"]

    with pytest.raises(ValidationError):
        CaseFile(**case, answer="")  # no answer yet
    with pytest.raises(ValidationError):
        CaseFile(**case, answer="Modest.", mood="optimistic")  # a field nobody agreed on


async def test_a_saved_case_crosses_to_the_second_graph(make_model: Callable) -> None:
    shared = InMemorySaver()  # one store for both graphs, as Redis is in Compose
    handoff = {"to": "writer", "reason": "The notes answer the question."}
    network = build_network_graph(
        make_model(
            [
                AIMessage("Energy is 18.5% of the portfolio."),
                AIMessage("", tool_calls=[{"name": "Handoff", "args": handoff, "id": "h1"}]),
                AIMessage("Energy is a modest 18.5% of the portfolio."),
            ]
        ),
        checkpointer=shared,
    )
    briefing = build_briefing_graph(
        make_model([AIMessage("Energy is 18.5% of C-1042's portfolio. No action needed.")]),
        checkpointer=shared,
    )
    network_thread = {"configurable": {"thread_id": case_thread("network", "amina", CASE_ID)}}
    await network.ainvoke(TEAM_INPUT, config=network_thread, context=CONTEXT)

    case = await export_case(network, "amina", CASE_ID)
    briefing_thread = {"configurable": {"thread_id": case_thread("briefing", "amina", CASE_ID)}}
    result = await briefing.ainvoke({"case": case.model_dump()}, config=briefing_thread)

    assert case.answer == "Energy is a modest 18.5% of the portfolio."
    assert result["briefing"].startswith("Energy is 18.5%")
    # The briefing graph saved its own work; the network's state is untouched
    assert "briefing" not in (await network.aget_state(network_thread)).values
    with pytest.raises(CaseNotFound):
        await export_case(network, "omar", CASE_ID)  # another analyst's namespace is empty
