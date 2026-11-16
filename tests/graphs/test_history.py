"""Time travel (Lab 36): every checkpoint of a thread can be read, and a run can start again
from any of them."""

from collections.abc import Callable
from unittest.mock import AsyncMock

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.research import build_research_graph
from sovereign_brain.memory.threads import thread_config, thread_key
from sovereign_brain.services.portfolio import PortfolioService

CONTEXT = ResearchContext(portfolio=AsyncMock(spec=PortfolioService), analyst="amina")
QUESTION = {
    "client_id": "C-1042",
    "client_profile": "Amina Rahman Holdings, private-banking, risk profile moderate",
    "question": "What is a bond?",
}


async def test_the_history_has_one_checkpoint_per_step(make_model: Callable) -> None:
    graph = build_research_graph(
        make_model([AIMessage("A bond is a debt security.")]), checkpointer=InMemorySaver()
    )
    config = thread_config(thread_key("amina", "bond-basics"))
    await graph.ainvoke(QUESTION, config=config, context=CONTEXT)

    history = [snapshot async for snapshot in graph.aget_state_history(config)]

    assert [s.metadata["step"] for s in history] == [3, 2, 1, 0, -1]
    assert [s.next for s in history] == [
        (),
        ("explain",),
        ("classify",),
        ("intake",),
        ("__start__",),
    ]
    assert history[-1].metadata["source"] == "input"
    parent = history[0].parent_config["configurable"]["checkpoint_id"]
    assert parent == history[1].config["configurable"]["checkpoint_id"]


async def test_a_run_can_start_again_from_an_earlier_checkpoint(make_model: Callable) -> None:
    replies = [AIMessage("A bond is a debt security."), AIMessage("A bond is a loan you make.")]
    graph = build_research_graph(make_model(replies), checkpointer=InMemorySaver())
    config = thread_config(thread_key("amina", "bond-basics"))
    await graph.ainvoke(QUESTION, config=config, context=CONTEXT)
    history = [snapshot async for snapshot in graph.aget_state_history(config)]
    before_explain = next(s for s in history if s.next == ("explain",))

    result = await graph.ainvoke(None, config=before_explain.config, context=CONTEXT)

    assert result["answer"] == "A bond is a loan you make."
    latest = (await graph.aget_state(config)).values
    assert latest["messages"][-1].content == "A bond is a loan you make."
    assert len(latest["messages"]) == 3  # the first answer is not on the new branch
    history = [snapshot async for snapshot in graph.aget_state_history(config)]
    assert "fork" in [s.metadata["source"] for s in history]
    assert "A bond is a debt security." in [s.values.get("answer") for s in history]
