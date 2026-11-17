"""The resilience protocol (Lab 43): tool errors go back to the model, with a retry limit."""

from collections.abc import Callable
from unittest.mock import AsyncMock

from langchain_core.messages import AIMessage

from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.research import GAVE_UP, build_research_graph
from sovereign_brain.graphs.trail import stations
from sovereign_brain.services.portfolio import PortfolioService

REQUEST = {
    "client_id": "C-1042",
    "client_profile": "Amina Rahman Holdings, private-banking, risk profile moderate",
    "question": "What would a 40% fall in energy stocks cost this portfolio?",
}
FORM = {
    "client_id": "C-1042",
    "sector": "Energy",
    "sector_value_usd": 185000,
    "portfolio_value_usd": 1000000,
    "shock_percent": 40,
    "risk_profile": "moderate",
}
TRAIL_AND_ANSWER = ["trail", "messages", "answer", "status", "checked"]


def stress_call(call_id: str, **change: object) -> AIMessage:
    """The model asks for a stress test; `change` puts mistakes into the form."""
    args = {**FORM, **change}
    return AIMessage("", tool_calls=[{"name": "stress_test", "args": args, "id": call_id}])


def context() -> ResearchContext:
    return ResearchContext(portfolio=AsyncMock(spec=PortfolioService), analyst="amina")


async def test_the_model_fixes_its_arguments_after_a_tool_error(make_model: Callable) -> None:
    answer = AIMessage("A 40% fall would cost 74,000 USD, 7.4% of the portfolio.")
    model = make_model([stress_call("call-1", shock_percent=400), stress_call("call-2"), answer])
    graph = build_research_graph(model)

    result = await graph.ainvoke(REQUEST, context=context(), output_keys=TRAIL_AND_ANSWER)

    first_result = result["messages"][3]
    assert first_result.status == "error"
    assert first_result.content.startswith("Tool error (")
    assert [e["note"] for e in result["trail"] if e["node"] == "analyse"] == [
        "Asked for tools: stress_test",
        "Tool error 1 of 2 allowed: stress_test",
        "Asked for tools: stress_test",
        "Draft answer written",
    ]
    assert result["answer"] == answer.content
    assert result["checked"] is True


async def test_the_desk_gives_up_after_too_many_tool_errors(make_model: Callable) -> None:
    model = make_model([stress_call(f"call-{n}", shock_percent=400) for n in range(3)])
    graph = build_research_graph(model)

    result = await graph.ainvoke(REQUEST, context=context(), output_keys=TRAIL_AND_ANSWER)

    assert result["trail"][-1]["note"] == "Gave up after 3 tool errors: stress_test"
    assert "review" not in stations(result["trail"])
    assert result["status"] == "answered"
    assert result["checked"] is False
    assert result["answer"] == GAVE_UP
