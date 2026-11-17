"""A second, separate graph (Lab 54): the briefing for the client's relationship manager.

It knows nothing about the network's state. Its only input is a checked CaseFile, and it
saves its own work in the shared store under its own namespace ("briefing:...").
"""

from typing import TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

BRIEFING_PROMPT = (
    "You write two-sentence briefings for a bank's relationship managers. Summarise the "
    "team's answer for the client meeting, keeping every figure as written."
)


class BriefingInput(TypedDict):
    case: dict  # a CaseFile, as a dictionary (checked before it enters)


class BriefingState(BriefingInput):
    briefing: str


def build_briefing_graph(
    model: BaseChatModel, checkpointer: BaseCheckpointSaver | None = None
) -> CompiledStateGraph:
    async def brief(state: BriefingState) -> dict:
        case = state["case"]
        notes = "\n".join(f"- {note['author']}: {note['text']}" for note in case["notes"])
        request = (
            f"Client {case['client_id']}. Question: {case['question']}\n"
            f"Team notes:\n{notes}\nTeam answer: {case['answer']}"
        )
        reply = await model.ainvoke([SystemMessage(BRIEFING_PROMPT), HumanMessage(request)])
        return {"briefing": str(reply.content)}

    builder = StateGraph(BriefingState, input_schema=BriefingInput)
    builder.add_node("brief", brief)
    builder.add_edge(START, "brief")
    builder.add_edge("brief", END)
    return builder.compile(checkpointer=checkpointer, name="briefing")
