import itertools
from collections.abc import Callable
from typing import get_type_hints

import pytest
from langchain_core.messages import AIMessage
from langgraph.errors import GraphRecursionError

from sovereign_brain.graphs.research import ResearchState, build_research_graph, intake
from sovereign_brain.graphs.trail import stations

REQUEST = {
    "client_id": "C-1042",
    "client_profile": "Amina Rahman Holdings, private-banking, risk profile moderate",
    "question": "Energy exposure?",
}
TOOL_CALL = AIMessage(
    "",
    tool_calls=[
        {
            "name": "sector_exposure",
            "args": {"client_id": "C-1042", "sector": "Energy"},
            "id": "call-1",
        }
    ],
)
WRONG = AIMessage("Energy is 25% of the portfolio.")
RIGHT = AIMessage("Energy is 18.5% of the portfolio.")
# Tests may read the whole state; callers only get the output schema's fields
EVERYTHING = list(get_type_hints(ResearchState))


class StubPortfolio:
    """Stands in for PortfolioService: fixed figures, no database."""

    async def positions(self, client_id: str) -> dict:
        return {"client_id": client_id, "positions": []}

    async def sector_exposure(self, client_id: str, sector: str) -> dict:
        return {
            "client_id": client_id,
            "sector": sector,
            "sector_value_usd": 185000,
            "portfolio_value_usd": 1000000,
            "percent": 18.5,
        }


def test_intake_writes_the_first_messages() -> None:
    update = intake(REQUEST)

    assert stations(update["trail"]) == ["intake"]
    assert update["trail"][0]["note"] == "Request received for C-1042"
    assert update["status"] == "received"
    assert update["revisions"] == 0
    assert update["messages"][1].content == (
        "Client C-1042 (Amina Rahman Holdings, private-banking, risk profile moderate): "
        "Energy exposure?"
    )


async def test_reducers_append_the_trail_and_overwrite_status(make_model: Callable) -> None:
    model = make_model([AIMessage("Energy is a modest part of the portfolio.")])
    graph = build_research_graph(model, StubPortfolio())

    result = await graph.ainvoke(REQUEST, output_keys=EVERYTHING)

    assert stations(result["trail"]) == ["intake", "classify", "analyse", "review"]
    assert [entry["note"] for entry in result["trail"][1:]] == [
        "Route: portfolio",
        "Draft answer written",
        "Every figure is supported by the tool results",
    ]
    assert result["status"] == "answered"
    assert result["answer"] == "Energy is a modest part of the portfolio."
    assert [message.type for message in result["messages"]] == ["system", "human", "ai"]


async def test_the_agent_calls_a_tool_then_answers(make_model: Callable) -> None:
    model = make_model([TOOL_CALL, RIGHT])
    graph = build_research_graph(model, StubPortfolio())

    result = await graph.ainvoke(REQUEST, output_keys=EVERYTHING)

    assert stations(result["trail"]) == ["intake", "classify", "analyse", "analyse", "review"]
    assert result["trail"][2]["note"] == "Asked for tools: sector_exposure"
    types = [message.type for message in result["messages"]]
    assert types == ["system", "human", "ai", "tool", "ai"]
    assert '"percent": 18.5' in result["messages"][3].content
    assert result["answer"] == "Energy is 18.5% of the portfolio."
    assert result["checked"] is True


async def test_a_wrong_figure_is_sent_back_and_corrected(make_model: Callable) -> None:
    model = make_model([TOOL_CALL, WRONG, RIGHT])
    graph = build_research_graph(model, StubPortfolio())

    result = await graph.ainvoke(REQUEST, output_keys=EVERYTHING)

    assert stations(result["trail"]) == [
        "intake", "classify", "analyse", "analyse", "review", "analyse", "review",
    ]
    assert result["trail"][4]["note"] == "Sent back, unsupported: 25"
    note = result["messages"][5]
    assert note.name == "reviewer"
    assert "25" in note.content
    assert result["revisions"] == 1
    assert result["answer"] == "Energy is 18.5% of the portfolio."
    assert result["checked"] is True


async def test_the_review_gives_up_after_the_limit(make_model: Callable) -> None:
    model = make_model(itertools.cycle([WRONG]))  # always the same wrong figure
    graph = build_research_graph(model, StubPortfolio(), max_revisions=2)

    result = await graph.ainvoke(
        REQUEST, config={"recursion_limit": 12}, output_keys=EVERYTHING
    )

    assert result["revisions"] == 2
    assert stations(result["trail"]).count("review") == 3
    assert result["trail"][-1]["note"] == "Gave up after 2 revisions, unsupported: 25"
    assert result["status"] == "answered"
    assert result["checked"] is False


async def test_the_recursion_limit_stops_a_runaway_loop(make_model: Callable) -> None:
    model = make_model(itertools.cycle([TOOL_CALL]))  # asks for the tool forever
    graph = build_research_graph(model, StubPortfolio())

    with pytest.raises(GraphRecursionError):
        await graph.ainvoke(REQUEST, config={"recursion_limit": 12})


async def test_a_general_question_takes_the_explain_track(make_model: Callable) -> None:
    model = make_model([AIMessage("A moderate profile accepts some ups and downs.")])
    graph = build_research_graph(model, StubPortfolio())
    question = "What does a moderate risk profile mean?"

    result = await graph.ainvoke({**REQUEST, "question": question}, output_keys=EVERYTHING)

    assert result["route"] == "general"
    assert stations(result["trail"]) == ["intake", "classify", "explain"]
    assert result["answer"] == "A moderate profile accepts some ups and downs."


async def test_callers_receive_only_the_output_fields(make_model: Callable) -> None:
    graph = build_research_graph(make_model([TOOL_CALL, RIGHT]), StubPortfolio())

    result = await graph.ainvoke(REQUEST)

    assert result == {
        "answer": "Energy is 18.5% of the portfolio.",
        "route": "portfolio",
        "checked": True,
    }


async def test_fields_outside_the_input_schema_are_ignored(make_model: Callable) -> None:
    graph = build_research_graph(make_model([AIMessage("A bond is a loan.")]), StubPortfolio())
    forged = {**REQUEST, "question": "What is a bond?", "checked": True, "revisions": 9}

    result = await graph.ainvoke(forged)

    assert result == {"answer": "A bond is a loan.", "route": "general"}
