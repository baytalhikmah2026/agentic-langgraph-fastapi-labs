"""The Research Desk graph (Module 3): one graph that grows lab by lab.

Lab 21: a typed state with reducers, and two stations: intake and analyse.
Lab 22: analyse can call portfolio tools in a loop (the ReAct pattern).
Lab 23: classify picks a track: portfolio questions to analyse, general questions to explain.
Lab 24: review checks every figure of a portfolio answer and sends the draft back if needed.
Lab 25: input and output schemas: callers send three fields and receive only the answer fields.
Lab 26: an append-only audit trail: every station adds what it decided and when.
Lab 28: services and limits arrive with each run (context_schema), not at build time.
Lab 30: the model chooses the track (structured output); the word rules are the fallback.
Lab 31: a checkpointer keeps each thread's state, so follow-ups continue a conversation.
Lab 37: write_brief is shared with corrections, which rewrite a brief in an earlier checkpoint.
Lab 38: remember stores every finished answer in semantic memory (Qdrant), if it is on.
Lab 39: recall finds related earlier answers; the model reads them next to the thread.
Lab 40: the model reads only the newest part of a long thread (trim_messages).
Lab 42: the model is offered the whole tool wall: portfolio tools plus the stress test.
Lab 43: a failing tool becomes a message; the model may retry, up to max_tool_retries.
Lab 44: tools discovered on MCP servers join the wall (extra_tools).
Lab 45: the analyst may read the desk's research notes (notes MCP server).
Lab 46: current prices come from the market-data MCP server, never from memory.
Lab 47: calculations no tool covers are written as Python and run in the sandbox.
"""

import logging
import operator
from collections.abc import Sequence
from typing import Annotated, Literal, NotRequired, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    trim_messages,
)
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.runtime import Runtime
from pydantic import ValidationError

from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.review import unsupported_figures
from sovereign_brain.graphs.routing import ROUTER_PROMPT, Route, RouteDecision, classify_question
from sovereign_brain.graphs.trail import TrailEntry, mark
from sovereign_brain.memory.semantic import MemoryRecord, Recollection
from sovereign_brain.tools.errors import failed_tools, tool_error_message
from sovereign_brain.tools.registry import RESEARCH_TOOLS

logger = logging.getLogger("sovereign_brain.research")

RESEARCH_PROMPT = (
    "You are an analyst on the Research Desk of Crescent Ledger Bank. "
    "For questions about a client's holdings or exposure, call the tools first and "
    "quote only the figures they return. "
    "For a 'what if prices fall' question, call sector_exposure first, then stress_test "
    "with the figures it returned. "
    "When the question is about the desk's views or research notes, call list_notes and "
    "read_note if you have them, and say which note you used. "
    "For a current price, call get_quote if you have it; never take prices from memory notes. "
    "For a calculation no other tool does, write short Python that prints the result and "
    "call run_python. "
    "Answer in at most three sentences. "
    "If the tools have no data, say which data you would check."
)
MEMORY_NOTE = (
    "Notes from this analyst's earlier conversations about this client. They may be out "
    "of date: use them for context only, and take every figure from the tools.\n"
)
GAVE_UP = (
    "The Research Desk could not get the data for this question: a tool kept failing. "
    "Please try again later, or ask the desk team to check the tools."
)


class ResearchInput(TypedDict):
    """What a caller must send to start a run: nothing else is accepted into the state."""

    client_id: str
    client_profile: str
    question: str


class ResearchOutput(TypedDict):
    """What a caller receives at the end of a run: the answer, never the scratchpad."""

    answer: str
    route: Route
    checked: NotRequired[bool | None]  # only portfolio answers are checked


class ResearchState(ResearchInput):
    """Everything the graph knows about one research request (the input fields, plus these)."""

    messages: Annotated[list[AnyMessage], add_messages]  # appended: the talk with the model
    trail: Annotated[list[TrailEntry], operator.add]  # appended: what each station did (Lab 26)
    route: Route  # overwritten: general or portfolio (Lab 23)
    status: Literal["received", "drafted", "revising", "answered"]  # overwritten
    answer: str  # overwritten: the latest answer
    revisions: int  # overwritten: how often the review sent the draft back (Lab 24)
    checked: bool | None  # overwritten: True when every figure was found; None until checked
    recollections: list[dict]  # overwritten: related answers from other threads (Lab 39)


def write_brief(client_id: str, client_profile: str, question: str) -> str:
    """The message the model reads for one question: who the client is, and what is asked."""
    return f"Client {client_id} ({client_profile}): {question}"


def intake(state: ResearchState, runtime: Runtime[ResearchContext]) -> dict:
    """Turn the request into messages for the model (no AI in this step).

    A new thread starts with the system prompt; a follow-up only adds the new question.
    The per-question fields (status, revisions, checked) start again for every question.
    """
    brief = write_brief(state["client_id"], state["client_profile"], state["question"])
    first_turn = not state.get("messages")
    opening = [SystemMessage(RESEARCH_PROMPT)] if first_turn else []
    note = f"Request received for {state['client_id']} from {runtime.context.analyst}"
    return {
        "messages": [*opening, HumanMessage(brief)],
        "trail": mark("intake", note if first_turn else f"{note} (follow-up)"),
        "status": "received",
        "revisions": 0,
        "checked": None,
        "recollections": [],  # each question looks up its own memories (Lab 39)
    }


async def recall(
    state: ResearchState, config: RunnableConfig, runtime: Runtime[ResearchContext]
) -> dict:
    """Look up related answers from earlier conversations (Lab 39). Memory off: nothing to do.

    Answers from this same thread are left out: the thread already remembers them.
    """
    memory = runtime.context.memory
    if memory is None:
        return {}
    this_thread = config["configurable"].get("thread_id", "").partition(":")[2]
    try:
        found = await memory.recall(runtime.context.analyst, state["client_id"], state["question"])
    except Exception as error:  # without memory the desk still answers, just without notes
        logger.warning("Semantic memory not available for recall: %r", error)
        return {"trail": mark("recall", f"Memory not available: {type(error).__name__}")}
    related = [r for r in found if r.thread_id != this_thread]
    note = f"Related answers from earlier conversations: {len(related)}"
    return {
        "recollections": [r.model_dump(mode="json") for r in related],
        "trail": mark("recall", note),
    }


def with_memory(state: ResearchState, history_limit: int = 20) -> list[AnyMessage]:
    """What the model reads: the thread's messages, plus a note of related earlier answers.

    The note sits just before the newest question. It is built for each model call and never
    saved in the thread, so the conversation does not grow with old notes (Lab 39).
    Older turns are trimmed to `history_limit` messages; the current turn is never cut (Lab 40).
    """
    messages = list(state["messages"])
    newest = max(i for i, m in enumerate(messages) if m.type == "human" and m.name != "reviewer")
    older = trim_messages(
        messages[:newest],
        max_tokens=history_limit,  # with token_counter=len, "tokens" means messages
        token_counter=len,
        strategy="last",  # keep the most recent turns
        start_on="human",  # never start in the middle of a turn
        include_system=True,  # always keep the system prompt
    )
    current = messages[newest:]
    notes = []
    for item in state.get("recollections") or []:
        try:
            notes.append(Recollection.model_validate(item))
        except ValidationError:  # only well-formed memories may reach the model
            logger.warning("A recollection was left out: it does not match MemoryRecord")
    if not notes:
        return [*older, *current]
    lines = "\n".join(f"- {n.saved_at:%Y-%m-%d} Q: {n.question} A: {n.answer}" for n in notes)
    return [*older, SystemMessage(MEMORY_NOTE + lines), *current]


def classify(state: ResearchState) -> dict:
    """Choose a track by the word rules (Lab 23); the fallback of the model router."""
    route = classify_question(state["question"])
    return {"route": route, "trail": mark("classify", f"Route: {route}")}


def pick_track(state: ResearchState) -> Route:
    """The switch after classify: it only reads the route that classify wrote."""
    return state["route"]


def is_source(message: BaseMessage) -> bool:
    """Tool results and the analyst's brief count as sources; review notes do not."""
    return message.type == "tool" or (message.type == "human" and message.name != "reviewer")


def after_analyse(state: ResearchState) -> Literal["tools", "review", "done"]:
    """The switch after analyse: run the tools, review a draft, or stop after tool errors."""
    if state["status"] == "answered":  # analyse gave up (Lab 43)
        return "done"
    return "tools" if tools_condition(state) == "tools" else "review"


def after_review(state: ResearchState) -> Literal["revise", "done"]:
    """The switch after review: back to analyse, or on to the end."""
    return "revise" if state["status"] == "revising" else "done"


def review(state: ResearchState, runtime: Runtime[ResearchContext]) -> dict:
    """Check the draft: every figure must appear in the tool results or the brief."""
    sources = " ".join(str(m.content) for m in state["messages"] if is_source(m))
    unsupported = unsupported_figures(state["answer"], sources)
    if not unsupported:
        note = "Every figure is supported by the tool results"
        return {"trail": mark("review", note), "status": "answered", "checked": True}
    figures = ", ".join(unsupported)
    limit = runtime.context.max_revisions
    if state["revisions"] >= limit:
        note = f"Gave up after {limit} revisions, unsupported: {figures}"
        return {"trail": mark("review", note), "status": "answered", "checked": False}
    correction = HumanMessage(
        "Revise your answer. These figures are not in the tool results: "
        f"{figures}. Quote only figures returned by the tools.",
        name="reviewer",
    )
    return {
        "messages": [correction],
        "trail": mark("review", f"Sent back, unsupported: {figures}"),
        "status": "revising",
        "revisions": state["revisions"] + 1,
    }


async def remember(
    state: ResearchState, config: RunnableConfig, runtime: Runtime[ResearchContext]
) -> dict:
    """Store the finished answer in semantic memory (Lab 38). Memory off: nothing to do."""
    memory = runtime.context.memory
    if memory is None:
        return {}
    if state.get("checked") is False:
        return {"trail": mark("remember", "Not stored: some figures could not be checked")}
    key = config["configurable"].get("thread_id", "")  # "<username>:<thread_id>" (Lab 31)
    try:
        record = MemoryRecord(
            owner=runtime.context.analyst,
            client_id=state["client_id"],
            thread_id=key.partition(":")[2] or "-",
            question=state["question"],
            answer=state["answer"],
            route=state["route"],
        )
        await memory.remember(record)
    except Exception as error:  # memory is a bonus: an answer is never lost because of it
        logger.warning("Answer not stored in semantic memory: %r", error)
        return {"trail": mark("remember", f"Not stored: {type(error).__name__}")}
    return {"trail": mark("remember", "Answer stored in semantic memory")}


def build_research_graph(
    model: BaseChatModel,
    checkpointer: BaseCheckpointSaver | None = None,
    extra_tools: Sequence[BaseTool] = (),
) -> CompiledStateGraph:
    """Built once at start-up; each run brings its own ResearchContext.

    With a checkpointer (Lab 31), every run must name a thread in its configuration.
    `extra_tools` are added to the tool wall, for example the tools of MCP servers (Lab 44).
    """
    tools = [*RESEARCH_TOOLS, *extra_tools]
    model_with_tools = model.bind_tools(tools)
    router = model.with_structured_output(RouteDecision)

    async def choose_route(state: ResearchState, runtime: Runtime[ResearchContext]) -> dict:
        """The classify station: the model decides; the rules step in if it cannot."""
        if runtime.context.router == "rules":
            return classify(state)
        try:
            decision = await router.ainvoke(
                [SystemMessage(ROUTER_PROMPT), HumanMessage(state["question"])]
            )
        except Exception as error:  # a routing failure must never stop the request
            logger.warning("Model router failed, using the word rules: %r", error)
            decision = None
        if not isinstance(decision, RouteDecision):
            update = classify(state)
            update["trail"] = mark("classify", f"Route: {update['route']} (rules fallback)")
            return update
        note = f"Route: {decision.route} (model: {decision.reason})"
        return {"route": decision.route, "trail": mark("classify", note)}

    async def analyse(state: ResearchState, runtime: Runtime[ResearchContext]) -> dict:
        """Reason: the model either asks for tools or writes a draft answer.

        Failed tools come back as error messages (Lab 43). The model reads them and may try
        again; after more than max_tool_retries errors in one question, the desk gives up.
        """
        failed = failed_tools(state["messages"])
        limit = runtime.context.max_tool_retries
        if len(failed) > limit:
            names = ", ".join(sorted({m.name or "unknown" for m in failed}))
            return {
                "messages": [AIMessage(GAVE_UP)],
                "trail": mark("analyse", f"Gave up after {len(failed)} tool errors: {names}"),
                "status": "answered",
                "checked": False,  # nothing was checked, so remember will not store it
                "answer": GAVE_UP,
            }
        trail = []
        last = state["messages"][-1]
        if isinstance(last, ToolMessage) and last.status == "error":
            trail += mark("analyse", f"Tool error {len(failed)} of {limit} allowed: {last.name}")
        reply = await model_with_tools.ainvoke(with_memory(state, runtime.context.history_limit))
        if reply.tool_calls:
            names = ", ".join(call["name"] for call in reply.tool_calls)
            trail += mark("analyse", f"Asked for tools: {names}")
            return {"messages": [reply], "trail": trail}
        return {
            "messages": [reply],
            "trail": trail + mark("analyse", "Draft answer written"),
            "status": "drafted",
            "answer": str(reply.content),
        }

    async def explain(state: ResearchState, runtime: Runtime[ResearchContext]) -> dict:
        """Answer a general question directly: no tools, one model call."""
        reply = await model.ainvoke(with_memory(state, runtime.context.history_limit))
        return {
            "messages": [reply],
            "trail": mark("explain", "General answer written"),
            "status": "answered",
            "answer": str(reply.content),
        }

    builder = StateGraph(
        ResearchState,
        context_schema=ResearchContext,
        input_schema=ResearchInput,
        output_schema=ResearchOutput,
    )
    builder.add_node("intake", intake)
    builder.add_node("recall", recall)
    builder.add_node("classify", choose_route)
    builder.add_node("analyse", analyse)
    # act: run the requested tools; a failing tool answers with an error message (Lab 43)
    builder.add_node("tools", ToolNode(tools, handle_tool_errors=tool_error_message))
    builder.add_node("explain", explain)
    builder.add_node("review", review)
    builder.add_node("remember", remember)
    builder.add_edge(START, "intake")
    builder.add_edge("intake", "recall")
    builder.add_edge("recall", "classify")
    builder.add_conditional_edges(
        "classify", pick_track, {"portfolio": "analyse", "general": "explain"}
    )
    # tools, a draft for review, or (after too many tool errors) straight to remember
    builder.add_conditional_edges(
        "analyse", after_analyse, {"tools": "tools", "review": "review", "done": "remember"}
    )
    builder.add_edge("tools", "analyse")  # observe: the results go back to the model
    builder.add_conditional_edges(
        "review", after_review, {"revise": "analyse", "done": "remember"}
    )
    builder.add_edge("explain", "remember")
    builder.add_edge("remember", END)
    return builder.compile(name="research", checkpointer=checkpointer)
