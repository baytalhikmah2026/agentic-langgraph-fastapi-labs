from collections.abc import Callable

from langchain_core.messages import AIMessage

from sovereign_brain.graphs.research import build_research_graph, intake

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

    assert update["steps"] == ["intake"]
    assert update["status"] == "received"
    assert update["messages"][1].content == (
        "Client C-1042 (Amina Rahman Holdings, private-banking, risk profile moderate): "
        "Energy exposure?"
    )


async def test_reducers_append_steps_and_overwrite_status(make_model: Callable) -> None:
    model = make_model([AIMessage("Energy is 12% of the portfolio.")])
    graph = build_research_graph(model, StubPortfolio())

    result = await graph.ainvoke(REQUEST)

    assert result["steps"] == ["intake", "analyse"]
    assert result["status"] == "answered"
    assert result["answer"] == "Energy is 12% of the portfolio."
    assert [message.type for message in result["messages"]] == ["system", "human", "ai"]


async def test_the_agent_calls_a_tool_then_answers(make_model: Callable) -> None:
    model = make_model([TOOL_CALL, AIMessage("Energy is 18.5% of the portfolio.")])
    graph = build_research_graph(model, StubPortfolio())

    result = await graph.ainvoke(REQUEST)

    assert result["steps"] == ["intake", "analyse", "analyse"]
    types = [message.type for message in result["messages"]]
    assert types == ["system", "human", "ai", "tool", "ai"]
    assert '"percent": 18.5' in result["messages"][3].content
    assert result["answer"] == "Energy is 18.5% of the portfolio."
