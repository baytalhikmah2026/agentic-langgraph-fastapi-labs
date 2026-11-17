"""The Map-Reduce pattern (Lab 57): many readers at once for one long document.

split cuts the document into pieces. Send starts one summarise task per piece, all in the
same step, so they run at the same time (map). collect waits for all of them. If the
summaries together are still too long, they are grouped and summarised again (collapse),
round after round, up to a limit. reduce writes the final summary from the last round.
"""

import operator
from typing import Annotated, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Send

from sovereign_brain.graphs.trail import TrailEntry, mark
from sovereign_brain.services.documents import chunk_text, group_texts

MAP_PROMPT = (
    "Summarise this part of a bank research document in at most three sentences. Keep every "
    "figure as written, and keep what matters for the analyst's focus."
)
REDUCE_PROMPT = (
    "Combine these summaries of one document into a single summary of at most five sentences "
    "for the analyst's focus. Keep every figure as written."
)


class ChunkTask(TypedDict):
    """One reader's assignment: which piece, in which round, and what to look for."""

    index: int
    round: int
    text: str
    focus: str


class Summary(TypedDict):
    index: int
    round: int
    text: str


class DocInput(TypedDict):
    name: str
    text: str
    focus: str


class DocOutput(TypedDict):
    summary: str
    chunks: int
    rounds: int


class DocState(DocInput):
    pieces: list[str]  # overwritten: the pieces of the current round
    chunks: int
    rounds: int  # the current round: 1 for the document's own pieces
    summaries: Annotated[list[Summary], operator.add]  # appended by readers working at once
    summary: str
    trail: Annotated[list[TrailEntry], operator.add]


def latest(state: DocState) -> list[str]:
    """The summaries of the current round, in document order."""
    found = [s for s in state["summaries"] if s["round"] == state["rounds"]]
    return [s["text"] for s in sorted(found, key=lambda s: s["index"])]


def build_mapreduce_graph(
    model: BaseChatModel, chunk_chars: int = 1200, collapse_chars: int = 2000, max_rounds: int = 3
) -> CompiledStateGraph:
    async def split(state: DocState) -> dict:
        pieces = chunk_text(state["text"], chunk_chars)
        note = f"{len(pieces)} pieces of at most {chunk_chars} characters"
        return {"pieces": pieces, "chunks": len(pieces), "rounds": 1, "trail": mark("split", note)}

    def fan_out(state: DocState) -> list[Send]:
        """Map: one summarise task per piece, all started in the same step."""
        return [
            Send("summarise", ChunkTask(index=i, round=1, text=piece, focus=state["focus"]))
            for i, piece in enumerate(state["pieces"])
        ]

    async def summarise(task: ChunkTask) -> dict:
        """One reader, one piece. It sees only its own task, not the whole state."""
        request = f"Focus: {task['focus']}\n\n{task['text']}"
        reply = await model.ainvoke([SystemMessage(MAP_PROMPT), HumanMessage(request)])
        summary = Summary(index=task["index"], round=task["round"], text=str(reply.content))
        return {"summaries": [summary]}

    async def collect(state: DocState) -> dict:
        """Runs once, after every reader of the round has finished."""
        round_number = max(s["round"] for s in state["summaries"])
        texts = [s["text"] for s in state["summaries"] if s["round"] == round_number]
        note = f"Round {round_number}: {len(texts)} summaries, {sum(map(len, texts))} characters"
        return {"rounds": round_number, "trail": mark("collect", note)}

    def after_collect(state: DocState) -> list[Send] | str:
        """Collapse: too long for one final read? Group the summaries and read them again."""
        texts = latest(state)
        too_long = len(texts) > 1 and sum(map(len, texts)) > collapse_chars
        if not too_long or state["rounds"] >= max_rounds:
            return "reduce"
        next_round, focus = state["rounds"] + 1, state["focus"]
        return [
            Send("summarise", ChunkTask(index=i, round=next_round, text=group, focus=focus))
            for i, group in enumerate(group_texts(texts, collapse_chars))
        ]

    async def reduce(state: DocState) -> dict:
        joined = "\n".join(f"- {text}" for text in latest(state))
        request = f"Document: {state['name']}\nFocus: {state['focus']}\nSummaries:\n{joined}"
        reply = await model.ainvoke([SystemMessage(REDUCE_PROMPT), HumanMessage(request)])
        return {"summary": str(reply.content), "trail": mark("reduce", "Final summary written")}

    builder = StateGraph(DocState, input_schema=DocInput, output_schema=DocOutput)
    builder.add_node("split", split)
    builder.add_node("summarise", summarise)
    builder.add_node("collect", collect)
    builder.add_node("reduce", reduce)
    builder.add_edge(START, "split")
    builder.add_conditional_edges("split", fan_out, ["summarise"])
    builder.add_edge("summarise", "collect")
    builder.add_conditional_edges("collect", after_collect, ["summarise", "reduce"])
    builder.add_edge("reduce", END)
    return builder.compile(name="mapreduce")
