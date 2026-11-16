"""Unit tests for single stations of the research graph (Lab 29).

Each station is a plain function: give it a mock state (and a runtime), look at the
update it returns. No graph, no model, no database.
"""

from collections.abc import Callable
from typing import get_type_hints
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.runtime import Runtime

from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.research import (
    ResearchState,
    build_research_graph,
    classify,
    intake,
    review,
)
from sovereign_brain.services.portfolio import PortfolioService

STATE_FIELDS = set(get_type_hints(ResearchState))
EXPOSURE = {
    "client_id": "C-1042",
    "sector": "Energy",
    "sector_value_usd": 185000,
    "portfolio_value_usd": 1000000,
    "percent": 18.5,
}


@pytest.fixture
def portfolio() -> AsyncMock:
    """A stand-in for PortfolioService that records every call (a spy)."""
    service = AsyncMock(spec=PortfolioService)
    service.sector_exposure.return_value = EXPOSURE
    return service


@pytest.fixture
def runtime(portfolio: AsyncMock) -> Runtime[ResearchContext]:
    return Runtime(context=ResearchContext(portfolio=portfolio, analyst="amina", max_revisions=1))


def mock_state(answer: str, revisions: int = 0) -> ResearchState:
    """A research state as it looks when review starts: brief, tool result, draft."""
    return {
        "client_id": "C-1042",
        "client_profile": "Amina Rahman Holdings, private-banking, risk profile moderate",
        "question": "Energy exposure?",
        "messages": [
            SystemMessage("You are an analyst."),
            HumanMessage("Client C-1042: Energy exposure?"),
            ToolMessage(str(EXPOSURE), tool_call_id="call-1"),
            AIMessage(answer),
        ],
        "trail": [],
        "route": "portfolio",
        "status": "drafted",
        "answer": answer,
        "revisions": revisions,
    }


def assert_update(update: dict, expected_keys: set[str]) -> None:
    """A station returns only the fields it changes, and only real state fields."""
    assert set(update) == expected_keys
    assert set(update) <= STATE_FIELDS


def test_intake_returns_its_delta(runtime: Runtime[ResearchContext]) -> None:
    update = intake(mock_state(""), runtime)

    assert_update(update, {"messages", "trail", "status", "revisions"})


def test_classify_writes_only_the_route_and_the_trail() -> None:
    update = classify({"question": "What is a bond?"})

    assert_update(update, {"route", "trail"})
    assert update["route"] == "general"


def test_review_approves_supported_figures(runtime: Runtime[ResearchContext]) -> None:
    update = review(mock_state("Energy is 18.5% of the portfolio."), runtime)

    assert_update(update, {"trail", "status", "checked"})
    assert update["checked"] is True


def test_review_sends_a_wrong_figure_back(runtime: Runtime[ResearchContext]) -> None:
    update = review(mock_state("Energy is 25% of the portfolio."), runtime)

    assert_update(update, {"messages", "trail", "status", "revisions"})
    assert update["revisions"] == 1
    assert update["messages"][0].name == "reviewer"


def test_review_reads_its_limit_from_the_context(runtime: Runtime[ResearchContext]) -> None:
    update = review(mock_state("Energy is 25% of the portfolio.", revisions=1), runtime)

    assert_update(update, {"trail", "status", "checked"})
    assert update["checked"] is False


async def test_the_tools_station_calls_the_service(
    make_model: Callable, portfolio: AsyncMock
) -> None:
    tool_call = AIMessage(
        "",
        tool_calls=[
            {
                "name": "sector_exposure",
                "args": {"client_id": "C-1042", "sector": "Energy"},
                "id": "call-1",
            }
        ],
    )
    graph = build_research_graph(make_model([tool_call, AIMessage("Energy is 18.5%.")]))
    context = ResearchContext(portfolio=portfolio, analyst="amina")

    await graph.ainvoke(
        {"client_id": "C-1042", "client_profile": "moderate", "question": "Energy exposure?"},
        context=context,
    )

    portfolio.sector_exposure.assert_awaited_once_with("C-1042", "Energy")
    portfolio.positions.assert_not_awaited()
