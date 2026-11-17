"""Corrections (Lab 37): a question is changed at an earlier checkpoint, and a new branch
runs from there while the original run stays in the history."""

from collections.abc import Callable
from unittest.mock import AsyncMock

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.research import build_research_graph
from sovereign_brain.memory.corrections import correct_question
from sovereign_brain.memory.threads import thread_config, thread_key
from sovereign_brain.services.portfolio import PortfolioService

CONTEXT = ResearchContext(portfolio=AsyncMock(spec=PortfolioService), analyst="amina")
PROFILE = "Amina Rahman Holdings, private-banking, risk profile moderate"
QUESTION = {"client_id": "C-1042", "client_profile": PROFILE, "question": "What is a bond?"}


async def test_a_corrected_question_runs_on_a_new_branch(make_model: Callable) -> None:
    replies = [AIMessage("A bond is a debt security."), AIMessage("A share is part of a company.")]
    graph = build_research_graph(make_model(replies), checkpointer=InMemorySaver())
    config = thread_config(thread_key("amina", "basics"))
    await graph.ainvoke(QUESTION, config=config, context=CONTEXT)
    history = [snapshot async for snapshot in graph.aget_state_history(config)]
    after_intake = next(s for s in history if s.next == ("recall",))

    corrected = await correct_question(graph, after_intake, "What is a share?", "amina")

    update = await graph.aget_state(corrected)
    assert update.metadata["source"] == "update"
    assert update.next == ("recall",)
    parent = update.parent_config["configurable"]["checkpoint_id"]
    assert parent == after_intake.config["configurable"]["checkpoint_id"]
    result = await graph.ainvoke(None, config=corrected, context=CONTEXT)
    assert result["answer"] == "A share is part of a company."
    latest = (await graph.aget_state(config)).values
    assert latest["question"] == "What is a share?"
    questions = [m.content for m in latest["messages"] if m.type == "human"]
    assert questions == [f"Client C-1042 ({PROFILE}): What is a share?"]  # replaced, not added
    assert latest["trail"][1]["note"] == "Question corrected by amina"
    old_answers = [s.values.get("answer") async for s in graph.aget_state_history(config)]
    assert "A bond is a debt security." in old_answers
