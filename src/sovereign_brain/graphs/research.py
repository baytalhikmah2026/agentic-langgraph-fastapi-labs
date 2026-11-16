"""The Research Desk graph (Module 3): one graph that grows lab by lab.

Lab 21: a typed state with reducers, and two stations: intake and analyse.
Lab 22: analyse can call portfolio tools in a loop (the ReAct pattern).
Lab 23: classify picks a track: portfolio questions to analyse, general questions to explain.
Lab 24: review checks every figure of a portfolio answer and sends the draft back if needed.
Lab 25: input and output schemas: callers send three fields and receive only the answer fields.
Lab 26: an append-only audit trail: every station adds what it decided and when.
Lab 28: services and limits arrive with each run (context_schema), not at build time.
Lab 30: the model chooses the track (structured output); the word rules are the fallback.
"""

import logging
import operator
from typing import Annotated, Literal, NotRequired, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AnyMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.runtime import Runtime

from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.review import unsupported_figures
from sovereign_brain.graphs.routing import ROUTER_PROMPT, Route, RouteDecision, classify_question
from sovereign_brain.graphs.trail import TrailEntry, mark
from sovereign_brain.tools.portfolio import PORTFOLIO_TOOLS

logger = logging.getLogger("sovereign_brain.research")

RESEARCH_PROMPT = (
    "You are an analyst on the Research Desk of Crescent Ledger Bank. "
    "For questions about a client's holdings or exposure, call the tools first and "
    "quote only the figures they return. "
    "Answer in at most three sentences. "
    "If the tools have no data, say which data you would check."
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
    checked: NotRequired[bool]  # only portfolio answers are checked


class ResearchState(ResearchInput):
    """Everything the graph knows about one research request (the input fields, plus these)."""

    messages: Annotated[list[AnyMessage], add_messages]  # appended: the talk with the model
    trail: Annotated[list[TrailEntry], operator.add]  # appended: what each station did (Lab 26)
    route: Route  # overwritten: general or portfolio (Lab 23)
    status: Literal["received", "drafted", "revising", "answered"]  # overwritten
    answer: str  # overwritten: the latest answer
    revisions: int  # overwritten: how often the review sent the draft back (Lab 24)
    checked: bool  # overwritten: True when every figure was found in the tool results


def intake(state: ResearchState, runtime: Runtime[ResearchContext]) -> dict:
    """Turn the request into the first messages for the model (no AI in this step)."""
    brief = f"Client {state['client_id']} ({state['client_profile']}): {state['question']}"
    note = f"Request received for {state['client_id']} from {runtime.context.analyst}"
    return {
        "messages": [SystemMessage(RESEARCH_PROMPT), HumanMessage(brief)],
        "trail": mark("intake", note),
        "status": "received",
        "revisions": 0,
    }


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


def build_research_graph(model: BaseChatModel) -> CompiledStateGraph:
    """Built once at start-up; each run brings its own ResearchContext."""
    model_with_tools = model.bind_tools(PORTFOLIO_TOOLS)
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

    async def analyse(state: ResearchState) -> dict:
        """Reason: the model either asks for tools or writes a draft answer."""
        reply = await model_with_tools.ainvoke(state["messages"])
        if reply.tool_calls:
            names = ", ".join(call["name"] for call in reply.tool_calls)
            return {"messages": [reply], "trail": mark("analyse", f"Asked for tools: {names}")}
        return {
            "messages": [reply],
            "trail": mark("analyse", "Draft answer written"),
            "status": "drafted",
            "answer": str(reply.content),
        }

    async def explain(state: ResearchState) -> dict:
        """Answer a general question directly: no tools, one model call."""
        reply = await model.ainvoke(state["messages"])
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
    builder.add_node("classify", choose_route)
    builder.add_node("analyse", analyse)
    builder.add_node("tools", ToolNode(PORTFOLIO_TOOLS))  # act: run the requested tools
    builder.add_node("explain", explain)
    builder.add_node("review", review)
    builder.add_edge(START, "intake")
    builder.add_edge("intake", "classify")
    builder.add_conditional_edges(
        "classify", pick_track, {"portfolio": "analyse", "general": "explain"}
    )
    # tools_condition answers "tools" or END; a finished draft now goes to review instead
    builder.add_conditional_edges("analyse", tools_condition, {"tools": "tools", END: "review"})
    builder.add_edge("tools", "analyse")  # observe: the results go back to the model
    builder.add_conditional_edges("review", after_review, {"revise": "analyse", "done": END})
    builder.add_edge("explain", END)
    return builder.compile(name="research")
