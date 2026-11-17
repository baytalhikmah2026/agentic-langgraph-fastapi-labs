"""A team inside the team (Lab 52): the research desk as a sub-graph and as one worker."""

from collections.abc import Callable
from unittest.mock import AsyncMock

from langchain_core.messages import AIMessage
from langchain_core.tools import StructuredTool

from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.team.research_desk import build_desk_graph, desk_members
from sovereign_brain.graphs.team.supervisor import Delegation, build_team_graph, guard
from sovereign_brain.graphs.trail import stations
from sovereign_brain.services.portfolio import PortfolioService

CONTEXT = ResearchContext(portfolio=AsyncMock(spec=PortfolioService), analyst="amina")
DESK_INPUT = {
    "client_id": "C-1042",
    "client_profile": "Amina Rahman Holdings, private-banking, risk profile moderate",
    "task": "What do the notes say about Gulf Petroleum, and what is its price?",
}
TEAM_INPUT = {**{k: DESK_INPUT[k] for k in ("client_id", "client_profile")},
              "question": DESK_INPUT["task"]}


async def read_note(name: str) -> str:
    """The full text of one research note."""
    return "Rating: hold."


async def get_quote(ticker: str) -> str:
    """The latest internal price of one stock."""
    return '{"ticker": "GLFP", "price": 62.4}'


# Stand-ins for the tools of the notes and market MCP servers
DESK_TOOLS = [
    StructuredTool.from_function(coroutine=read_note, name="read_note"),
    StructuredTool.from_function(coroutine=get_quote, name="get_quote"),
]
# The two members work at the same time, so either one may get either reply
MEMBER_REPLIES = [AIMessage("The desk rates it hold."), AIMessage("GLFP is at 62.4 USD.")]


def test_each_member_gets_only_its_own_tools() -> None:
    members = desk_members(DESK_TOOLS)

    assert {name: [t.name for t in tools] for name, tools in members.items()} == {
        "librarian": ["read_note"],
        "pricer": ["get_quote"],
    }
    assert desk_members([]) == {}


async def test_the_desk_works_in_parallel_and_hands_back_one_summary(
    make_model: Callable,
) -> None:
    summary = AIMessage("Gulf Petroleum is rated hold and trades at 62.4 USD.")
    desk = build_desk_graph(make_model([*MEMBER_REPLIES, summary]), DESK_TOOLS)

    result = await desk.ainvoke(DESK_INPUT, context=CONTEXT)

    assert sorted(f.split(":")[0] for f in result["findings"]) == ["librarian", "pricer"]
    assert result["summary"] == summary.content


async def test_the_supervisor_sees_only_the_desk_summary(make_model: Callable) -> None:
    def delegate(next_worker: str, call_id: str) -> AIMessage:
        args = {"next": next_worker, "task": "Your part, please."}
        return AIMessage("", tool_calls=[{"name": "Delegation", "args": args, "id": call_id}])

    summary = "Gulf Petroleum is rated hold and trades at 62.4 USD."
    model = make_model(
        [
            delegate("research_desk", "d1"),
            *MEMBER_REPLIES,
            AIMessage(summary),
            delegate("writer", "d2"),
            AIMessage("Gulf Petroleum: hold, 62.4 USD."),
            delegate("finish", "d3"),
        ]
    )
    graph = build_team_graph(model, extra_tools=DESK_TOOLS)

    result = await graph.ainvoke(
        TEAM_INPUT, context=CONTEXT, output_keys=["answer", "notes", "trail"]
    )

    assert stations(result["trail"]) == [
        "supervisor", "research_desk", "supervisor", "writer", "supervisor",
    ]
    assert result["notes"] == [{"author": "research_desk", "text": summary}]


def test_without_desk_tools_the_analyst_goes_instead() -> None:
    decision = Delegation(next="research_desk", task="Read the notes.")

    checked = guard(decision, {}, max_turns=6, desk_ready=False)

    assert (checked.next, checked.task) == ("analyst", "Read the notes.")
