"""Plan-and-execute (Lab 56): a flight plan, flown step by step, replanned when a step fails."""

from collections.abc import Callable
from unittest.mock import AsyncMock

from langchain_core.messages import AIMessage

from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.team.planner import FALLBACK_PLAN, build_planner_graph
from sovereign_brain.graphs.trail import stations
from sovereign_brain.services.portfolio import PortfolioService

TEAM_INPUT = {
    "client_id": "C-1042",
    "client_profile": "Amina Rahman Holdings, private-banking, risk profile moderate",
    "question": "Prepare a risk review of the energy holdings.",
}
KEYS = ["answer", "completed", "trail"]


def context(max_replans: int = 2) -> ResearchContext:
    portfolio = AsyncMock(spec=PortfolioService)
    return ResearchContext(portfolio=portfolio, analyst="amina", max_replans=max_replans)


def plan(*goals: str, call_id: str = "p1") -> AIMessage:
    args = {"steps": [{"goal": goal} for goal in goals]}
    return AIMessage("", tool_calls=[{"name": "Plan", "args": args, "id": call_id}])


async def test_the_plan_is_flown_step_by_step(make_model: Callable) -> None:
    model = make_model(
        [
            plan("Find the energy exposure.", "Stress-test a 40% energy fall."),
            AIMessage("Energy is 185,000 USD, 18.5% of the portfolio."),
            AIMessage("A 40% fall costs 7.4%; the limit is 5%."),
            AIMessage("Energy is 18.5%; a 40% fall would breach the 5% limit."),
        ]
    )
    graph = build_planner_graph(model)

    result = await graph.ainvoke(TEAM_INPUT, context=context(), output_keys=KEYS)

    assert stations(result["trail"]) == ["plan", "execute", "execute", "finish"]
    assert [step["status"] for step in result["completed"]] == ["done", "done"]
    assert result["answer"].startswith("Energy is 18.5%")


async def test_a_failed_step_leads_to_a_new_plan(make_model: Callable) -> None:
    model = make_model(
        [
            plan("Look up bond prices.", "Stress-test a 40% energy fall."),
            AIMessage("FAILED: there is no tool for bond prices."),
            plan("Stress-test a 40% energy fall.", call_id="p2"),
            AIMessage("A 40% fall costs 7.4%; the limit is 5%."),
            AIMessage("A 40% energy fall would breach the 5% limit."),
        ]
    )
    graph = build_planner_graph(model)

    result = await graph.ainvoke(TEAM_INPUT, context=context(), output_keys=KEYS)

    assert stations(result["trail"]) == ["plan", "execute", "replan", "execute", "finish"]
    assert [step["status"] for step in result["completed"]] == ["failed", "done"]


async def test_without_replans_left_the_trip_ends_with_what_was_done(
    make_model: Callable,
) -> None:
    model = make_model(
        [
            plan("Look up bond prices.", "Stress-test a 40% energy fall."),
            AIMessage("FAILED: there is no tool for bond prices."),
            AIMessage("The review could not be completed: no bond prices are available."),
        ]
    )
    graph = build_planner_graph(model)

    result = await graph.ainvoke(TEAM_INPUT, context=context(max_replans=0), output_keys=KEYS)

    assert stations(result["trail"]) == ["plan", "execute", "finish"]


async def test_an_unreadable_plan_falls_back_to_one_step(make_model: Callable) -> None:
    model = make_model(
        [
            AIMessage("Let me think about a plan..."),  # no Plan at all
            AIMessage("Energy is 185,000 USD, 18.5% of the portfolio."),
            AIMessage("Energy is 18.5% of the portfolio."),
        ]
    )
    graph = build_planner_graph(model)

    result = await graph.ainvoke(TEAM_INPUT, context=context(), output_keys=KEYS)

    assert [step["goal"] for step in result["completed"]] == FALLBACK_PLAN
