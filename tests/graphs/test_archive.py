"""Knowledge nuggets (Lab 40): a thread is summarised into semantic memory."""

from collections.abc import Callable
from unittest.mock import AsyncMock

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.research import build_research_graph
from sovereign_brain.memory.semantic import SemanticMemory
from sovereign_brain.memory.summaries import ThreadArchivist
from sovereign_brain.memory.threads import thread_config, thread_key
from sovereign_brain.services.portfolio import PortfolioService

PROFILE = "Amina Rahman Holdings, private-banking, risk profile moderate"
BOND = {"client_id": "C-1042", "client_profile": PROFILE, "question": "What is a bond?"}
SUMMARY = "The analyst asked what a bond is; the desk explained that a bond is a loan."


async def test_a_thread_becomes_a_knowledge_nugget(
    make_model: Callable, make_memory: Callable[[], SemanticMemory]
) -> None:
    memory = make_memory()
    context = ResearchContext(portfolio=AsyncMock(spec=PortfolioService), analyst="amina")
    graph = build_research_graph(
        make_model([AIMessage("A bond is a loan to a company.")]), checkpointer=InMemorySaver()
    )
    key = thread_key("amina", "bond-basics")
    await graph.ainvoke(BOND, config=thread_config(key), context=context)
    archivist = ThreadArchivist(make_model([AIMessage(SUMMARY)]), memory)

    summary = await archivist.archive(graph, key)

    assert summary == SUMMARY
    [nugget] = await memory.recall("amina", "C-1042", "bond")
    assert nugget.question == "Summary of the conversation bond-basics"
    assert nugget.answer == SUMMARY
    assert await archivist.archive(graph, thread_key("amina", "no-such-thread")) is None
