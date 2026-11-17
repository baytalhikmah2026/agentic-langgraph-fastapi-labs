"""The remember station (Lab 38): finished answers go to semantic memory, never at any cost."""

from collections.abc import Callable
from unittest.mock import AsyncMock

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.runtime import Runtime

from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.research import build_research_graph, remember
from sovereign_brain.graphs.trail import stations
from sovereign_brain.memory.semantic import SemanticMemory
from sovereign_brain.memory.threads import thread_config, thread_key
from sovereign_brain.services.portfolio import PortfolioService

PROFILE = "Amina Rahman Holdings, private-banking, risk profile moderate"
QUESTION = {"client_id": "C-1042", "client_profile": PROFILE, "question": "What is a bond?"}


def context_with(memory: SemanticMemory) -> ResearchContext:
    return ResearchContext(
        portfolio=AsyncMock(spec=PortfolioService), analyst="amina", memory=memory
    )


async def test_a_finished_answer_is_remembered(
    make_model: Callable, make_memory: Callable[[], SemanticMemory]
) -> None:
    memory = make_memory()
    graph = build_research_graph(
        make_model([AIMessage("A bond is a loan to a company.")]), checkpointer=InMemorySaver()
    )
    config = thread_config(thread_key("amina", "bond-basics"))

    result = await graph.ainvoke(
        QUESTION, config=config, context=context_with(memory), output_keys=["answer", "trail"]
    )

    assert stations(result["trail"]) == ["intake", "classify", "explain", "remember"]
    assert result["trail"][-1]["note"] == "Answer stored in semantic memory"
    [found] = await memory.recall("amina", "C-1042", "What is a bond?")
    assert found.thread_id == "bond-basics"
    assert found.answer == "A bond is a loan to a company."


async def test_an_unchecked_answer_is_not_remembered(
    make_memory: Callable[[], SemanticMemory],
) -> None:
    memory = make_memory()
    state = {
        **QUESTION,
        "answer": "Energy is 42% of the portfolio.",
        "route": "portfolio",
        "checked": False,
    }

    update = await remember(state, {"configurable": {}}, Runtime(context=context_with(memory)))

    assert update["trail"][0]["note"] == "Not stored: some figures could not be checked"
    assert await memory.recall("amina", "C-1042", "energy") == []


async def test_the_answer_survives_when_memory_is_down(make_model: Callable) -> None:
    broken = AsyncMock(spec=SemanticMemory)
    broken.remember.side_effect = ConnectionError("Qdrant is not reachable")
    graph = build_research_graph(make_model([AIMessage("A bond is a loan to a company.")]))

    result = await graph.ainvoke(
        QUESTION, context=context_with(broken), output_keys=["answer", "trail"]
    )

    assert result["answer"] == "A bond is a loan to a company."
    assert result["trail"][-1]["note"] == "Not stored: ConnectionError"
