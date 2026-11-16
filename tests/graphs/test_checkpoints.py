"""Checkpointers (Lab 32): threads kept in a SQLite file survive a restart."""

from collections.abc import Callable
from pathlib import Path
from unittest.mock import AsyncMock

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

from sovereign_brain.core.settings import Settings
from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.research import build_research_graph
from sovereign_brain.memory.checkpoints import open_checkpointer
from sovereign_brain.memory.threads import thread_config, thread_key
from sovereign_brain.services.portfolio import PortfolioService

CONTEXT = ResearchContext(portfolio=AsyncMock(spec=PortfolioService), analyst="amina")
QUESTION = {
    "client_id": "C-1042",
    "client_profile": "Amina Rahman Holdings, private-banking, risk profile moderate",
    "question": "What is a bond?",
}


async def test_sqlite_threads_survive_a_restart(tmp_path: Path, make_model: Callable) -> None:
    file = tmp_path / "checkpoints.sqlite"
    settings = Settings(checkpoint_store="sqlite", checkpoint_sqlite_path=str(file))
    config = thread_config(thread_key("amina", "restart-test"))

    async with open_checkpointer(settings) as saver:  # the API runs ...
        graph = build_research_graph(make_model([AIMessage("A bond is a loan.")]), saver)
        await graph.ainvoke(QUESTION, config=config, context=CONTEXT)

    async with open_checkpointer(settings) as saver:  # ... stops, and starts again
        graph = build_research_graph(make_model([]), saver)
        saved = (await graph.aget_state(config)).values

    assert file.exists()
    assert saved["answer"] == "A bond is a loan."
    assert [m.type for m in saved["messages"]] == ["system", "human", "ai"]


async def test_the_memory_store_is_the_default() -> None:
    async with open_checkpointer(Settings(checkpoint_store="memory")) as saver:
        assert isinstance(saver, InMemorySaver)
