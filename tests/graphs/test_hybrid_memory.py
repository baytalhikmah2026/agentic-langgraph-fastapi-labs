"""Hybrid memory (Lab 39): a thread remembers its own turns, Qdrant remembers the others."""

from collections.abc import Callable
from unittest.mock import AsyncMock

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.research import build_research_graph
from sovereign_brain.memory.semantic import SemanticMemory
from sovereign_brain.memory.threads import thread_config, thread_key
from sovereign_brain.services.portfolio import PortfolioService

PROFILE = "Amina Rahman Holdings, private-banking, risk profile moderate"
BOND = {"client_id": "C-1042", "client_profile": PROFILE, "question": "What is a bond?"}
BOND_RISK = {**BOND, "question": "What is the risk of a bond?"}
REPLIES = [AIMessage("A bond is a loan to a company."), AIMessage("Its main risk is default.")]


def context_with(memory: SemanticMemory) -> ResearchContext:
    return ResearchContext(
        portfolio=AsyncMock(spec=PortfolioService), analyst="amina", memory=memory
    )


async def test_a_new_thread_recalls_answers_from_earlier_threads(
    make_model: Callable, make_memory: Callable[[], SemanticMemory]
) -> None:
    context = context_with(make_memory())
    graph = build_research_graph(make_model(REPLIES), checkpointer=InMemorySaver())
    await graph.ainvoke(
        BOND, config=thread_config(thread_key("amina", "bond-basics")), context=context
    )
    second = thread_config(thread_key("amina", "bond-risk"))

    await graph.ainvoke(BOND_RISK, config=second, context=context)

    state = (await graph.aget_state(second)).values
    [note] = state["recollections"]
    assert note["thread_id"] == "bond-basics"
    assert note["answer"] == "A bond is a loan to a company."
    assert state["trail"][1]["note"] == "Related answers from earlier conversations: 1"
    assert len(state["messages"]) == 3  # prompt, question, answer: the note is never saved


async def test_a_thread_does_not_recall_its_own_answers(
    make_model: Callable, make_memory: Callable[[], SemanticMemory]
) -> None:
    context = context_with(make_memory())
    graph = build_research_graph(make_model(REPLIES), checkpointer=InMemorySaver())
    config = thread_config(thread_key("amina", "bond-basics"))
    await graph.ainvoke(BOND, config=config, context=context)

    await graph.ainvoke(BOND_RISK, config=config, context=context)

    state = (await graph.aget_state(config)).values
    assert state["recollections"] == []
    recall_notes = [entry["note"] for entry in state["trail"] if entry["node"] == "recall"]
    assert recall_notes[-1] == "Related answers from earlier conversations: 0"
