"""Resuming (Lab 35): an interrupted run continues from its last checkpoint."""

from collections.abc import Callable
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.research import build_research_graph
from sovereign_brain.graphs.trail import stations
from sovereign_brain.memory.threads import thread_config, thread_key
from sovereign_brain.services.portfolio import PortfolioService

CONTEXT = ResearchContext(portfolio=AsyncMock(spec=PortfolioService), analyst="amina")
QUESTION = {
    "client_id": "C-1042",
    "client_profile": "Amina Rahman Holdings, private-banking, risk profile moderate",
    "question": "What is a bond?",
}


async def test_a_run_resumes_where_it_stopped(make_flaky_model: Callable) -> None:
    graph = build_research_graph(
        make_flaky_model([AIMessage("A bond is a debt security.")]), checkpointer=InMemorySaver()
    )
    config = thread_config(thread_key("amina", "bond-basics"))

    with pytest.raises(ConnectionError):
        await graph.ainvoke(QUESTION, config=config, context=CONTEXT)
    stopped = await graph.aget_state(config)
    result = await graph.ainvoke(None, config=config, context=CONTEXT)

    assert stopped.next == ("explain",)
    assert stations(stopped.values["trail"]) == ["intake", "classify"]
    assert result["answer"] == "A bond is a debt security."
    saved = (await graph.aget_state(config)).values
    assert stations(saved["trail"]) == ["intake", "classify", "explain"]
    assert [m.type for m in saved["messages"]] == ["system", "human", "ai"]


async def test_a_new_question_replaces_the_interrupted_run(make_flaky_model: Callable) -> None:
    graph = build_research_graph(
        make_flaky_model([AIMessage("A share is a part of a company.")]),
        checkpointer=InMemorySaver(),
    )
    config = thread_config(thread_key("amina", "bond-basics"))

    with pytest.raises(ConnectionError):
        await graph.ainvoke(QUESTION, config=config, context=CONTEXT)
    result = await graph.ainvoke(
        {**QUESTION, "question": "What is a share?"}, config=config, context=CONTEXT
    )

    assert result["answer"] == "A share is a part of a company."
    saved = (await graph.aget_state(config)).values
    assert stations(saved["trail"]) == ["intake", "classify", "intake", "classify", "explain"]
    assert [m.type for m in saved["messages"]] == ["system", "human", "human", "ai"]
