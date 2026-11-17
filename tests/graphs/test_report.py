"""The report graph (Lab 49): forced facts, structured drafts, a guardrail and a fallback."""

import itertools
from collections.abc import Callable

from langchain_core.messages import AIMessage

from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.report import build_report_graph
from sovereign_brain.graphs.trail import stations

REQUEST = {
    "client_id": "C-1042",
    "client_profile": "Amina Rahman Holdings, private-banking, risk profile moderate",
}
GOOD = {
    "client_id": "C-1042",
    "headline": "Financials make up 81.5% of the portfolio, a high concentration.",
    "largest_sector": "Financials",
    "largest_sector_percent": 81.5,
    "risk_level": "high",
    "key_points": ["Medina Bank is worth 815000 USD.", "Energy holdings total 185000 USD."],
}
WRONG = {**GOOD, "largest_sector_percent": 75, "risk_level": "medium"}
EVERYTHING = ["report", "attempts", "checked", "trail"]


def as_report(fields: dict, call_id: str) -> AIMessage:
    """How a fake model hands back structured output: a call to the ResearchReport schema."""
    return AIMessage("", tool_calls=[{"name": "ResearchReport", "args": fields, "id": call_id}])


class StubPortfolio:
    """The C-1042 positions from the test database, without a database."""

    async def positions(self, client_id: str) -> dict:
        return {
            "client_id": client_id,
            "positions": [
                {"ticker": "MDNB", "name": "Medina Bank", "sector": "Financials",
                 "market_value_usd": 815000},
                {"ticker": "GLFP", "name": "Gulf Petroleum Co", "sector": "Energy",
                 "market_value_usd": 120000},
                {"ticker": "SNRS", "name": "Sunrise Solar", "sector": "Energy",
                 "market_value_usd": 65000},
            ],
        }


CONTEXT = ResearchContext(portfolio=StubPortfolio(), analyst="amina")


async def test_a_correct_draft_passes_the_guardrail(make_model: Callable) -> None:
    graph = build_report_graph(make_model([as_report(GOOD, "r1")]))

    result = await graph.ainvoke(REQUEST, context=CONTEXT, output_keys=EVERYTHING)

    assert stations(result["trail"]) == ["gather", "draft", "check"]
    assert result["report"] == GOOD
    assert (result["attempts"], result["checked"]) == (1, True)


async def test_a_wrong_draft_is_sent_back_and_fixed(make_model: Callable) -> None:
    graph = build_report_graph(make_model([as_report(WRONG, "r1"), as_report(GOOD, "r2")]))

    result = await graph.ainvoke(REQUEST, context=CONTEXT, output_keys=EVERYTHING)

    assert result["trail"][2]["note"] == (
        "Sent back: largest_sector_percent must be 81.5; risk_level must be high"
    )
    assert result["report"] == GOOD
    assert (result["attempts"], result["checked"]) == (2, True)


async def test_unparseable_drafts_end_in_the_plain_report(make_model: Callable) -> None:
    graph = build_report_graph(make_model(itertools.cycle([AIMessage("Here is my report!")])))

    result = await graph.ainvoke(REQUEST, context=CONTEXT, output_keys=EVERYTHING)

    assert stations(result["trail"])[-1] == "fallback"
    assert result["report"]["largest_sector"] == "Financials"
    assert result["report"]["risk_level"] == "high"
    assert (result["attempts"], result["checked"]) == (3, False)
