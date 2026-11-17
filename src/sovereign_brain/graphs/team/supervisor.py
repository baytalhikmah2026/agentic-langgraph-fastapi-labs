"""The Supervisor pattern (Lab 51): an editor agent hands each step to a specialist.

The supervisor reads the request and the team's notes, picks who works next and gives them a
short task. Workers report back to the supervisor, never to each other:
- analyst: an agent with the portfolio and risk tools (built with create_agent);
- writer: writes the final answer from the team's notes.
Code rules keep the editor honest: no writer without notes, no finish without an answer, and a
turn limit. If the model's decision cannot be read, the same rules choose instead.
Lab 52: research_desk, a sub-team (its own graph) that reads notes and prices, joins the team.
"""

import logging
from collections.abc import Sequence
from typing import Literal

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from pydantic import BaseModel, Field

from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.team.research_desk import build_desk_graph
from sovereign_brain.graphs.team.state import TeamInput, TeamOutput, TeamState, team_brief
from sovereign_brain.graphs.trail import mark
from sovereign_brain.tools.portfolio import PORTFOLIO_TOOLS
from sovereign_brain.tools.risk import RISK_TOOLS

logger = logging.getLogger("sovereign_brain.team")

Worker = Literal["analyst", "research_desk", "writer", "finish"]

SUPERVISOR_PROMPT = (
    "You are the editor of the Research Desk team at Crescent Ledger Bank. Your workers: "
    "analyst (looks up the client's portfolio and runs stress tests), research_desk (a small "
    "team that reads the research notes and current prices) and writer (writes the final "
    "answer from the team's notes). Pick who works next and give them one short task. "
    "Pick writer once the notes answer the question, and finish once the answer is written."
)
ANALYST_PROMPT = (
    "You are the analyst on the Research Desk team. Use your tools to find the facts for "
    "your task, and reply with a short note that quotes only figures the tools returned."
)
WRITER_PROMPT = (
    "You are the writer on the Research Desk team. Answer the client question in at most "
    "three sentences, using only the team's notes and their figures."
)


class Delegation(BaseModel):
    """The editor's decision: who works next, and on what."""

    next: Worker = Field(
        description="analyst, research_desk, writer, or finish when the answer is written"
    )
    task: str = Field(max_length=300, description="One short instruction for that worker")


def rules_delegation(state: TeamState) -> Delegation:
    """The plain order of work: facts first, then the answer, then stop."""
    if not state.get("notes"):
        return Delegation(next="analyst", task="Collect the facts needed for the question.")
    if not state.get("answer"):
        return Delegation(next="writer", task="Write the final answer from the notes.")
    return Delegation(next="finish", task="Done.")


def guard(
    decision: Delegation, state: TeamState, max_turns: int, desk_ready: bool = True
) -> Delegation:
    """Code rules on top of the editor: the team never skips a step or runs forever."""
    rules = rules_delegation(state)
    if decision.next == "research_desk" and not desk_ready:
        return Delegation(next="analyst", task=decision.task)  # no desk tools: the analyst goes
    if decision.next == "writer" and not state.get("notes"):
        return rules  # nothing to write from yet
    if decision.next == "finish" and not state.get("answer"):
        return rules  # nobody has answered yet
    out_of_turns = state.get("turns", 0) + 1 >= max_turns
    if out_of_turns and decision.next in ("analyst", "research_desk") and state.get("notes"):
        return rules  # no more research: write with what we have, or finish
    return decision


def route(state: TeamState) -> Worker:
    """The switch after the supervisor: it only reads the decision."""
    return state["next"]


def build_team_graph(
    model: BaseChatModel, extra_tools: Sequence[BaseTool] = ()
) -> CompiledStateGraph:
    """Built once at start-up; each run brings its own ResearchContext (Lab 28)."""
    editor = model.with_structured_output(Delegation)
    analyst_agent = create_agent(
        model,
        tools=[*PORTFOLIO_TOOLS, *RISK_TOOLS, *extra_tools],
        system_prompt=ANALYST_PROMPT,
        context_schema=ResearchContext,
        name="analyst",
    )
    desk = build_desk_graph(model, extra_tools)  # None when no notes or price tools are loaded

    async def supervisor(state: TeamState, runtime: Runtime[ResearchContext]) -> dict:
        """The editor decides; if its answer cannot be read, the rules decide."""
        how = "model"
        try:
            decision = await editor.ainvoke(
                [SystemMessage(SUPERVISOR_PROMPT), HumanMessage(team_brief(state))]
            )
        except Exception as error:  # a broken decision must never stop the team
            logger.warning("Supervisor decision failed, using the rules: %r", error)
            decision = None
        if not isinstance(decision, Delegation):
            decision, how = rules_delegation(state), "rules"
        decision = guard(decision, state, runtime.context.max_team_turns, desk is not None)
        note = f"Next: {decision.next} ({how}): {decision.task}"
        return {
            "next": decision.next,
            "task": decision.task,
            "turns": state.get("turns", 0) + 1,
            "trail": mark("supervisor", note),
        }

    async def analyst(state: TeamState, runtime: Runtime[ResearchContext]) -> dict:
        """A full agent of its own: it may call tools several times before it replies."""
        request = f"{team_brief(state)}\nYour task: {state['task']}"
        result = await analyst_agent.ainvoke(
            {"messages": [HumanMessage(request)]}, context=runtime.context
        )
        note = str(result["messages"][-1].content)
        return {
            "notes": [{"author": "analyst", "text": note}],
            "trail": mark("analyst", "Note added"),
        }

    async def research_desk(state: TeamState, runtime: Runtime[ResearchContext]) -> dict:
        """The sub-team: a slice of the team's state goes in, one note comes back out."""
        result = await desk.ainvoke(
            {
                "client_id": state["client_id"],
                "client_profile": state["client_profile"],
                "task": state["task"],
            },
            context=runtime.context,
        )
        note = f"Desk note added ({len(result['findings'])} findings)"
        return {
            "notes": [{"author": "research_desk", "text": result["summary"]}],
            "trail": mark("research_desk", note),
        }

    async def writer(state: TeamState) -> dict:
        """Writes the answer from the notes: one model call, no tools."""
        request = f"{team_brief(state)}\nYour task: {state['task']}"
        reply = await model.ainvoke([SystemMessage(WRITER_PROMPT), HumanMessage(request)])
        return {"answer": str(reply.content), "trail": mark("writer", "Answer written")}

    builder = StateGraph(
        TeamState,
        context_schema=ResearchContext,
        input_schema=TeamInput,
        output_schema=TeamOutput,
    )
    builder.add_node("supervisor", supervisor)
    builder.add_node("analyst", analyst)
    builder.add_node("writer", writer)
    paths = {"analyst": "analyst", "writer": "writer", "finish": END}
    if desk is not None:
        builder.add_node("research_desk", research_desk)
        builder.add_edge("research_desk", "supervisor")
        paths["research_desk"] = "research_desk"
    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges("supervisor", route, paths)
    builder.add_edge("analyst", "supervisor")  # workers always report back to the editor
    builder.add_edge("writer", "supervisor")
    return builder.compile(name="team")
