"""Thread memory (Lab 31): a checkpointer keeps each conversation between runs."""

from collections.abc import Callable
from unittest.mock import AsyncMock

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.research import build_research_graph
from sovereign_brain.graphs.trail import stations
from sovereign_brain.memory.threads import thread_config, thread_key
from sovereign_brain.services.portfolio import PortfolioService

CONTEXT = ResearchContext(portfolio=AsyncMock(spec=PortfolioService), analyst="amina")
FIRST = {
    "client_id": "C-1042",
    "client_profile": "Amina Rahman Holdings, private-banking, risk profile moderate",
    "question": "What is a bond?",
}
FOLLOW_UP = {**FIRST, "question": "Is that a kind of loan, then?"}


async def test_a_thread_remembers_the_conversation(make_model: Callable) -> None:
    replies = [AIMessage("A bond is a debt security."), AIMessage("Yes: you lend money.")]
    graph = build_research_graph(make_model(replies), checkpointer=InMemorySaver())
    config = thread_config(thread_key("amina", "bond-basics"))

    await graph.ainvoke(FIRST, config=config, context=CONTEXT)
    result = await graph.ainvoke(FOLLOW_UP, config=config, context=CONTEXT)

    assert result["answer"] == "Yes: you lend money."
    saved = (await graph.aget_state(config)).values
    assert [m.type for m in saved["messages"]] == ["system", "human", "ai", "human", "ai"]
    assert stations(saved["trail"]) == ["intake", "classify", "explain"] * 2
    assert saved["trail"][3]["note"].endswith("(follow-up)")


async def test_threads_are_kept_apart(make_model: Callable) -> None:
    replies = [AIMessage("A bond is a debt security."), AIMessage("Shares are ownership.")]
    graph = build_research_graph(make_model(replies), checkpointer=InMemorySaver())
    bonds = thread_config(thread_key("amina", "bond-basics"))
    shares = thread_config(thread_key("amina", "share-basics"))

    await graph.ainvoke(FIRST, config=bonds, context=CONTEXT)
    await graph.ainvoke({**FIRST, "question": "What is a share?"}, config=shares, context=CONTEXT)

    assert len((await graph.aget_state(bonds)).values["messages"]) == 3
    assert len((await graph.aget_state(shares)).values["messages"]) == 3
    other_analyst = thread_config(thread_key("yusuf", "bond-basics"))
    assert (await graph.aget_state(other_analyst)).values == {}


async def test_each_question_gets_a_fresh_check(make_model: Callable) -> None:
    portfolio = AsyncMock(spec=PortfolioService)
    portfolio.sector_exposure.return_value = {"sector": "Energy", "percent": 18.5}
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
    replies = [tool_call, AIMessage("Energy is 18.5%."), AIMessage("It pools many bonds.")]
    graph = build_research_graph(make_model(replies), checkpointer=InMemorySaver())
    config = thread_config(thread_key("amina", "energy-review"))
    context = ResearchContext(portfolio=portfolio, analyst="amina")

    first = await graph.ainvoke(
        {**FIRST, "question": "Energy exposure?"}, config=config, context=context
    )
    second = await graph.ainvoke(
        {**FIRST, "question": "What is a bond fund?"}, config=config, context=context
    )

    assert first["checked"] is True
    assert second == {"answer": "It pools many bonds.", "route": "general", "checked": None}
