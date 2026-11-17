"""Corrections (Lab 37): change what the agent knew at an earlier checkpoint, then fork.

`aupdate_state` saves a new checkpoint on top of a chosen one, as if a station had written
the new values itself. Its source is "update" and its parent is the chosen checkpoint, so
the original run stays in the history, untouched.
"""

from langchain_core.messages import AnyMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import StateSnapshot

from sovereign_brain.graphs.research import write_brief
from sovereign_brain.graphs.trail import mark

# A question can be corrected right after intake: it has been read, nothing is decided yet
CORRECTABLE_NEXT = ("recall",)  # since Lab 39, recall follows intake


def latest_brief(messages: list[AnyMessage]) -> AnyMessage:
    """The analyst's newest question in the conversation (review notes are not questions)."""
    return next(m for m in reversed(messages) if m.type == "human" and m.name != "reviewer")


async def correct_question(
    graph: CompiledStateGraph, snapshot: StateSnapshot, question: str, analyst: str
) -> RunnableConfig:
    """Save a corrected question on top of `snapshot` and return the new checkpoint's config.

    The new brief keeps the old brief's message ID, so add_messages replaces it in place
    instead of adding a second question.
    """
    values = snapshot.values
    old_brief = latest_brief(values["messages"])
    new_brief = HumanMessage(
        write_brief(values["client_id"], values["client_profile"], question), id=old_brief.id
    )
    return await graph.aupdate_state(
        snapshot.config,
        {
            "question": question,
            "messages": [new_brief],
            "trail": mark("intake", f"Question corrected by {analyst}"),
        },
        as_node="intake",  # as if intake had read the corrected question: recall runs next
    )
