"""Knowledge nuggets (Lab 40): an aging thread is summarised into semantic memory.

A thread cannot grow forever and is erased when it expires (Lab 34). Before that happens,
the model writes a short summary of the conversation, and the summary is stored in Qdrant
like any remembered answer. The conversation goes; what was learned stays findable.
"""

import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langgraph.graph.state import CompiledStateGraph

from sovereign_brain.memory.semantic import MemoryRecord, SemanticMemory
from sovereign_brain.memory.threads import thread_config

logger = logging.getLogger("sovereign_brain.memory")

SUMMARY_PROMPT = (
    "Summarise this conversation between an analyst and the Research Desk of Crescent "
    "Ledger Bank in at most five sentences. Keep the client facts and figures as they were "
    "stated, and say which questions were answered."
)


def conversation_text(messages: list[AnyMessage]) -> str:
    """The questions and answers of a thread as plain text: no prompt, tools or review notes."""
    lines = []
    for message in messages:
        if message.type == "human" and message.name != "reviewer":
            lines.append(f"Analyst: {message.content}")
        elif message.type == "ai" and message.content:
            lines.append(f"Research Desk: {message.content}")
    return "\n".join(lines)


class ThreadArchivist:
    """Turns a thread into one knowledge nugget in semantic memory."""

    def __init__(self, model: BaseChatModel, memory: SemanticMemory) -> None:
        self.model = model
        self.memory = memory

    async def archive(self, graph: CompiledStateGraph, key: str) -> str | None:
        """Summarise the thread stored under `key` into memory; None if there is no thread."""
        snapshot = await graph.aget_state(thread_config(key))
        if not snapshot.values:
            return None
        values = snapshot.values
        owner, _, thread_id = key.partition(":")
        reply = await self.model.ainvoke(
            [SystemMessage(SUMMARY_PROMPT), HumanMessage(conversation_text(values["messages"]))]
        )
        summary = str(reply.content)
        await self.memory.remember(
            MemoryRecord(
                owner=owner,
                client_id=values["client_id"],
                thread_id=thread_id,
                question=f"Summary of the conversation {thread_id}",
                answer=summary,
                route=values.get("route") or "general",
            )
        )
        logger.info("Thread %s summarised into semantic memory", key)
        return summary
