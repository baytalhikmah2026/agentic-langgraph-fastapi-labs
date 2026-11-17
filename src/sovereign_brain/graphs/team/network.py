"""The Network pattern (Lab 53): peers hand the work to each other, with no editor.

Every peer does its part, then decides who is best placed to continue and hands over
directly with Command(goto=...). Nobody sits in the middle. Code rules keep the network
honest: no handing to yourself, no writer without notes, and a hop limit after which the
work goes to the writer. The writer always ends the run.
"""

import logging
from collections.abc import Awaitable, Callable, Sequence
from typing import Literal

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from langgraph.types import Command
from pydantic import BaseModel, Field

from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.team.state import TeamInput, TeamOutput, TeamState, team_brief
from sovereign_brain.graphs.trail import mark
from sovereign_brain.tools.portfolio import PORTFOLIO_TOOLS
from sovereign_brain.tools.risk import RISK_TOOLS

logger = logging.getLogger("sovereign_brain.team")

Peer = Literal["analyst", "risk_officer", "writer"]
PEERS: tuple[Peer, ...] = ("analyst", "risk_officer", "writer")

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


class Handoff(BaseModel):
    """A peer's decision: who continues, and why."""

    to: Peer = Field(description="analyst, risk_officer or writer")
    reason: str = Field(max_length=200, description="One short sentence: why this peer")


def settle(handoff: Handoff, sender: Peer, state: TeamState, max_hops: int) -> Handoff:
    """Code rules on top of the peers' choice: never to yourself, never round in circles."""
    if handoff.to == sender:
        others = [peer for peer in PEERS if peer not in (sender, "writer")]
        return Handoff(to=others[0], reason="Handed on: a peer never hands work to itself.")
    if handoff.to == "writer" and not state.get("notes"):
        return Handoff(to="analyst", reason="No notes yet: the facts come first.")
    if state.get("turns", 0) + 1 >= max_hops and state.get("notes"):
        return Handoff(to="writer", reason="Hop limit reached: write with the notes we have.")
    return handoff


def peer_node(
    name: Peer, agent: CompiledStateGraph, decider: BaseChatModel
) -> Callable[..., Awaitable[Command[Peer]]]:
    """A peer as a node: its own agent loop, one note, then a direct handoff."""

    async def work(state: TeamState, runtime: Runtime[ResearchContext]) -> Command[Peer]:
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
        handoff = settle(handoff, name, after, runtime.context.max_team_turns)
        return Command(
            goto=handoff.to,
            update={
                "notes": [note],
                "next": handoff.to,
                "task": handoff.reason,
                "turns": state.get("turns", 0) + 1,
                "trail": mark(name, f"Handoff to {handoff.to}: {handoff.reason}"),
            },
        )

    return work


def build_network_graph(
    model: BaseChatModel, extra_tools: Sequence[BaseTool] = ()
) -> CompiledStateGraph:
    """Built once at start-up; each run brings its own ResearchContext (Lab 28)."""
    decider = model.with_structured_output(Handoff)
    tools = {
        "analyst": [*PORTFOLIO_TOOLS, *extra_tools],
        "risk_officer": [*PORTFOLIO_TOOLS, *RISK_TOOLS],
    }

    async def writer(state: TeamState) -> Command:
        """Writes the answer from the notes and ends the run."""
        request = f"{team_brief(state)}\nWrite the final answer."
        reply = await model.ainvoke([SystemMessage(WRITER_PROMPT), HumanMessage(request)])
        update = {"answer": str(reply.content), "trail": mark("writer", "Answer written")}
        return Command(goto=END, update=update)

    builder = StateGraph(
        TeamState, context_schema=ResearchContext, input_schema=TeamInput, output_schema=TeamOutput
    )
    for name in ("analyst", "risk_officer"):
        agent = create_agent(
            model,
            tools=tools[name],
            system_prompt=PEER_PROMPTS[name],
            context_schema=ResearchContext,
            name=name,
        )
        builder.add_node(name, peer_node(name, agent, decider), destinations=PEERS)
    builder.add_node("writer", writer, destinations=(END,))
    builder.add_edge(START, "analyst")  # the analyst opens; after that, the peers decide
    return builder.compile(name="network")
