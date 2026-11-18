"""Human approval (Labs 61-64): pauses, rejection, and feedback that goes back to the desk."""

import json
from collections.abc import Callable
from pathlib import Path

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.report import build_report_graph
from sovereign_brain.graphs.trail import mark, stations

APPROVAL_ID = "4b7e1c9a2d5f4e3b8a6c0d1e2f3a4b5c"
CONFIG = {"configurable": {"thread_id": f"approval:{APPROVAL_ID}"}}
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


async def test_the_run_stops_before_deliver(make_model: Callable, tmp_path: Path) -> None:
    graph = build_report_graph(
        make_model([as_report(GOOD, "r1")]), checkpointer=InMemorySaver(), outbox=tmp_path
    )

    await graph.ainvoke(REQUEST, config=CONFIG, context=CONTEXT)
    snapshot = await graph.aget_state(CONFIG)

    assert snapshot.next == ("deliver",)  # waiting for a person
    assert snapshot.values["report"] == GOOD
    assert list(tmp_path.iterdir()) == []  # nothing has been sent


async def test_released_the_report_is_delivered(make_model: Callable, tmp_path: Path) -> None:
    graph = build_report_graph(
        make_model([as_report(GOOD, "r1")]), checkpointer=InMemorySaver(), outbox=tmp_path
    )
    await graph.ainvoke(REQUEST, config=CONFIG, context=CONTEXT)

    result = await graph.ainvoke(None, config=CONFIG, context=CONTEXT)  # None = carry on

    letter = json.loads((tmp_path / f"{APPROVAL_ID}.json").read_text(encoding="utf-8"))
    assert letter["report"] == GOOD
    assert result["delivered"].endswith(f"{APPROVAL_ID}.json")
    assert stations((await graph.aget_state(CONFIG)).values["trail"])[-1] == "deliver"


async def test_an_inspection_pause_comes_right_after_the_draft(
    make_model: Callable, tmp_path: Path
) -> None:
    graph = build_report_graph(
        make_model([as_report(GOOD, "r1")]), checkpointer=InMemorySaver(), outbox=tmp_path
    )

    await graph.ainvoke(REQUEST, config=CONFIG, context=CONTEXT, interrupt_after=["draft"])
    after_draft = await graph.aget_state(CONFIG)
    await graph.ainvoke(None, config=CONFIG, context=CONTEXT)  # carry on to the next hold line
    before_deliver = await graph.aget_state(CONFIG)

    assert after_draft.next == ("check",)  # the draft is written, not yet checked
    assert after_draft.values["report"] == GOOD
    assert before_deliver.next == ("deliver",)  # the run-time pause applied only once


async def test_a_rejected_report_is_never_sent(make_model: Callable, tmp_path: Path) -> None:
    graph = build_report_graph(
        make_model([as_report(GOOD, "r1")]), checkpointer=InMemorySaver(), outbox=tmp_path
    )
    await graph.ainvoke(REQUEST, config=CONFIG, context=CONTEXT)

    note = mark("deliver", "Rejected by omar: no comment")
    await graph.aupdate_state(CONFIG, {"trail": note}, as_node="deliver")  # as if deliver ran
    snapshot = await graph.aget_state(CONFIG)

    assert snapshot.next == ()  # the run is over
    assert "delivered" not in snapshot.values
    assert list(tmp_path.iterdir()) == []  # and nothing was sent


async def test_feedback_sends_the_report_back_to_draft(
    make_model: Callable, tmp_path: Path
) -> None:
    better = {**GOOD, "headline": "Medina Bank alone is 81.5% of the portfolio."}
    graph = build_report_graph(
        make_model([as_report(GOOD, "r1"), as_report(better, "r2")]),
        checkpointer=InMemorySaver(),
        outbox=tmp_path,
    )
    await graph.ainvoke(REQUEST, config=CONFIG, context=CONTEXT)

    update = {"feedback": ["omar: Name the bank."], "verdict": "retry"}
    await graph.aupdate_state(CONFIG, update, as_node="check")  # as if check sent it back
    sent_back = await graph.aget_state(CONFIG)
    await graph.ainvoke(None, config=CONFIG, context=CONTEXT)
    redrafted = await graph.aget_state(CONFIG)

    assert sent_back.next == ("draft",)
    assert redrafted.next == ("deliver",)  # back at the hold line, waiting again
    assert redrafted.values["report"] == better
    assert redrafted.values["feedback"] == ["omar: Name the bank."]
    assert redrafted.values["attempts"] == 2
