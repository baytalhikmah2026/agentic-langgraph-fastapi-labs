"""The Network pattern (Lab 53): peers hand the work to each other, with no editor.

Every peer does its part, then decides who is best placed to continue and hands over
directly with Command(goto=...). Nobody sits in the middle. Code rules keep the network
honest: no handing to yourself and no writer without notes. The writer always ends the run.
Lab 54: with a checkpointer, every run is saved as a case in the shared store.
Lab 58: every handoff passes a watchdog. It counts down a TTL, notices when the peers stop
adding anything new (a gridlock), and then rolls the notebook back to the last safe state
and sends the work to the writer.
"""

import logging
import operator
from collections.abc import Awaitable, Callable, Sequence
from typing import Annotated, Literal

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from langgraph.types import Command
from pydantic import BaseModel, Field

from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.team.state import TeamInput, TeamOutput, WorkNote, team_brief
from sovereign_brain.graphs.trail import TrailEntry, mark
from sovereign_brain.tools.portfolio import PORTFOLIO_TOOLS
from sovereign_brain.tools.risk import RISK_TOOLS

logger = logging.getLogger("sovereign_brain.team")

Peer = Literal["analyst", "risk_officer", "writer"]
PEERS: tuple[Peer, ...] = ("analyst", "risk_officer", "writer")
STALL_LIMIT = 2  # handoffs in a row without new information before the watchdog steps in

PEER_PROMPTS = {
    "analyst": "You are the analyst in a team of peers at Crescent Ledger Bank. Use your tools "
    "to find the portfolio facts for the question, and reply with a short note that quotes "
    "only figures the tools returned.",
    "risk_officer": "You are the risk officer in a team of peers at Crescent Ledger Bank. Use "
    "your tools to judge the risk in the question (stress tests, loss limits), and reply with "
    "a short note that quotes only figures the tools returned.",
}
HANDOFF_PROMPT = (
    "You work in a team of peers: analyst (portfolio facts), risk_officer (stress tests and "
    "loss limits) and writer (writes the final answer). You have just added your note. Decide "
    "who is best placed to continue, and say why in one short sentence. Hand to writer once "
    "the notes answer the question."
)
WRITER_PROMPT = (
    "You are the writer in a team of peers. Answer the client question in at most three "
    "sentences, using only the team's notes and their figures."
)


def roll_back(keep: int) -> dict:
    """An instruction for the notebook: keep only the first `keep` notes."""
    return {"keep_notes": keep}


def notebook(notes: list[WorkNote], update: list[WorkNote] | dict) -> list[WorkNote]:
    """The notebook's reducer: new notes are appended; a roll_back cuts back to a safe state."""
    if isinstance(update, dict):
        return notes[: update["keep_notes"]]
    return notes + update


class NetworkState(TeamInput):
    notes: Annotated[list[WorkNote], notebook]  # appended, or rolled back by the watchdog
    next: str  # overwritten: the peer that was asked to continue
    task: str  # overwritten: why that peer was chosen
    turns: int  # overwritten: handoffs so far
    answer: str
    ttl: int  # overwritten: handoffs left before the writer must take over
    stalled: int  # overwritten: handoffs in a row that added no new information
    safe_notes: int  # overwritten: notes in the notebook at the last real progress
    trail: Annotated[list[TrailEntry], operator.add]


class Handoff(BaseModel):
    """A peer's decision: who continues, and why."""

    to: Peer = Field(description="analyst, risk_officer or writer")
    reason: str = Field(max_length=200, description="One short sentence: why this peer")


def settle(handoff: Handoff, sender: Peer, state: NetworkState) -> Handoff:
    """Code rules on top of the peers' choice: never to yourself, never write without notes."""
    if handoff.to == sender:
        others = [peer for peer in PEERS if peer not in (sender, "writer")]
        return Handoff(to=others[0], reason="Handed on: a peer never hands work to itself.")
    if handoff.to == "writer" and not state.get("notes"):
        return Handoff(to="analyst", reason="No notes yet: the facts come first.")
    return handoff


def same_text(text: str) -> str:
    """Notes are compared without case, spacing or final full stops."""
    return " ".join(text.lower().split()).rstrip(".")


def peer_node(
    name: Peer, agent: CompiledStateGraph, decider: BaseChatModel
) -> Callable[..., Awaitable[Command[Literal["watchdog"]]]]:
    """A peer as a node: its own agent loop, one note, then a handoff through the watchdog."""

    async def work(
        state: NetworkState, runtime: Runtime[ResearchContext]
    ) -> Command[Literal["watchdog"]]:
        request = f"{team_brief(state)}\nYour part: {state.get('task') or state['question']}"
        result = await agent.ainvoke({"messages": [HumanMessage(request)]}, context=runtime.context)
        note = {"author": name, "text": str(result["messages"][-1].content)}
        after = {**state, "notes": [*state.get("notes", []), note]}
        try:
            briefing = f"You are {name}.\n{team_brief(after)}"
            handoff = await decider.ainvoke([SystemMessage(HANDOFF_PROMPT), HumanMessage(briefing)])
        except Exception as error:  # a broken decision must never stop the team
            logger.warning("Handoff decision of %s failed: %r", name, error)
            handoff = None
        if not isinstance(handoff, Handoff):
            handoff = Handoff(to="writer", reason="Decision unreadable: the writer takes over.")
        handoff = settle(handoff, name, after)
        return Command(
            goto="watchdog",
            update={
                "notes": [note],
                "next": handoff.to,
                "task": handoff.reason,
                "turns": state.get("turns", 0) + 1,
                "trail": mark(name, f"Handoff to {handoff.to}: {handoff.reason}"),
            },
        )

    return work


async def watchdog(state: NetworkState, runtime: Runtime[ResearchContext]) -> Command[Peer]:
    """Every handoff passes here: count down the TTL, spot a gridlock, break it safely."""
    ttl = state.get("ttl", runtime.context.max_team_turns) - 1
    notes = state["notes"]
    earlier = {same_text(note["text"]) for note in notes[:-1]}
    if same_text(notes[-1]["text"]) in earlier:  # nothing new was added
        stalled, safe_notes = state.get("stalled", 0) + 1, state.get("safe_notes", 0)
    else:
        stalled, safe_notes = 0, len(notes)
    update = {"ttl": ttl, "stalled": stalled, "safe_notes": safe_notes}
    if stalled >= STALL_LIMIT:
        note = f"Gridlock: {stalled} handoffs with nothing new; back to {safe_notes} notes"
        logger.warning("%s (client %s)", note, state["client_id"])
        update |= {"notes": roll_back(safe_notes), "next": "writer", "task": note}
        return Command(goto="writer", update=update | {"trail": mark("watchdog", note)})
    if ttl <= 0 and state["next"] != "writer":
        note = "TTL expired: the writer takes over with the notes so far"
        update |= {"next": "writer", "task": note}
        return Command(goto="writer", update=update | {"trail": mark("watchdog", note)})
    note = f"Handoff to {state['next']} approved (ttl {ttl})"
    return Command(goto=state["next"], update=update | {"trail": mark("watchdog", note)})


def build_network_graph(
    model: BaseChatModel,
    extra_tools: Sequence[BaseTool] = (),
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    """Built once at start-up; each run brings its own ResearchContext (Lab 28)."""
    decider = model.with_structured_output(Handoff)
    tools = {
        "analyst": [*PORTFOLIO_TOOLS, *extra_tools],
        "risk_officer": [*PORTFOLIO_TOOLS, *RISK_TOOLS],
    }

    async def writer(state: NetworkState) -> Command:
        """Writes the answer from the notes and ends the run."""
        request = f"{team_brief(state)}\nWrite the final answer."
        reply = await model.ainvoke([SystemMessage(WRITER_PROMPT), HumanMessage(request)])
        update = {"answer": str(reply.content), "trail": mark("writer", "Answer written")}
        return Command(goto=END, update=update)

    builder = StateGraph(
        NetworkState,
        context_schema=ResearchContext,
        input_schema=TeamInput,
        output_schema=TeamOutput,
    )
    for name in ("analyst", "risk_officer"):
        agent = create_agent(
            model,
            tools=tools[name],
            system_prompt=PEER_PROMPTS[name],
            context_schema=ResearchContext,
            name=name,
        )
        builder.add_node(name, peer_node(name, agent, decider), destinations=("watchdog",))
    builder.add_node("watchdog", watchdog, destinations=PEERS)
    builder.add_node("writer", writer, destinations=(END,))
    builder.add_edge(START, "analyst")  # the analyst opens; after that, the peers decide
    return builder.compile(checkpointer=checkpointer, name="network")
