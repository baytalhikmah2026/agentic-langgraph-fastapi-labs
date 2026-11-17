"""A team inside the team (Lab 52): the research desk, a sub-graph used as one worker.

The desk has its own members and its own private state. Its members work at the same time
(parallel branches), each with only its own tools, and add their findings to the desk's
state. A summariser then condenses them into one note. The supervisor only ever sees that
note: the desk's internal back-and-forth stays inside the desk.
"""

import operator
from collections.abc import Awaitable, Callable, Sequence
from typing import Annotated, TypedDict

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime

from sovereign_brain.graphs.context import ResearchContext

# Desk members and the tools each one may use (tools from the MCP servers, Labs 45-48)
DESK_MEMBERS = {
    "librarian": ("list_notes", "read_note"),
    "pricer": ("get_quote", "get_quotes"),
}
MEMBER_PROMPTS = {
    "librarian": "You are the research desk's librarian. Read the research notes that matter "
    "for the task and report what they say, naming each note you used.",
    "pricer": "You are the research desk's pricer. Look up the current prices that matter "
    "for the task and report them with their date.",
}
SUMMARY_PROMPT = (
    "You lead the research desk. Combine your members' findings into one short note for the "
    "editor. Keep every figure, date and source as written."
)


class DeskInput(TypedDict):
    client_id: str
    client_profile: str
    task: str


class DeskOutput(TypedDict):
    summary: str
    findings: list[str]


class DeskState(DeskInput):
    findings: Annotated[list[str], operator.add]  # appended, even by members working at once
    summary: str


def desk_members(tools: Sequence[BaseTool]) -> dict[str, list[BaseTool]]:
    """Each member gets only its own tools; a member without tools stays home."""
    by_name = {tool.name: tool for tool in tools}
    members = {}
    for member, names in DESK_MEMBERS.items():
        own = [by_name[name] for name in names if name in by_name]
        if own:
            members[member] = own
    return members


def member_node(member: str, agent: CompiledStateGraph) -> Callable[..., Awaitable[dict]]:
    """A desk member as a node: its own agent loop, one finding back."""

    async def work(state: DeskState, runtime: Runtime[ResearchContext]) -> dict:
        request = f"Client {state['client_id']} ({state['client_profile']}). Task: {state['task']}"
        result = await agent.ainvoke({"messages": [HumanMessage(request)]}, context=runtime.context)
        return {"findings": [f"{member}: {result['messages'][-1].content}"]}

    return work


def build_desk_graph(
    model: BaseChatModel, tools: Sequence[BaseTool]
) -> CompiledStateGraph | None:
    """The desk's own graph: members in parallel, then the summary. None without members."""
    members = desk_members(tools)
    if not members:
        return None

    async def summarise(state: DeskState) -> dict:
        findings = "\n".join(f"- {finding}" for finding in state["findings"])
        request = f"Task: {state['task']}\nFindings:\n{findings}"
        reply = await model.ainvoke([SystemMessage(SUMMARY_PROMPT), HumanMessage(request)])
        return {"summary": str(reply.content)}

    builder = StateGraph(
        DeskState, context_schema=ResearchContext, input_schema=DeskInput, output_schema=DeskOutput
    )
    for member, own_tools in members.items():
        agent = create_agent(
            model,
            tools=own_tools,
            system_prompt=MEMBER_PROMPTS[member],
            context_schema=ResearchContext,
            name=member,
        )
        builder.add_node(member, member_node(member, agent))
        builder.add_edge(START, member)  # every member starts at the same time
    builder.add_node("summarise", summarise)
    builder.add_edge(list(members), "summarise")  # waits until every member has reported
    builder.add_edge("summarise", END)
    return builder.compile(name="research_desk")
