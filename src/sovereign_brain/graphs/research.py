"""The Research Desk graph (Module 3): one graph that grows lab by lab.

Lab 21: a typed state with reducers, and two stations: intake and analyse.
Lab 22: analyse can call portfolio tools in a loop (the ReAct pattern).
Lab 23: classify picks a track: portfolio questions to analyse, general questions to explain.
Lab 24: review checks every figure of a portfolio answer and sends the draft back if needed.
Lab 25: input and output schemas: callers send three fields and receive only the answer fields.
"""

import operator
from typing import Annotated, Literal, NotRequired, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AnyMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from sovereign_brain.graphs.review import unsupported_figures
from sovereign_brain.graphs.routing import Route, classify_question
from sovereign_brain.services.portfolio import PortfolioService
from sovereign_brain.tools.portfolio import build_portfolio_tools

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
    steps: Annotated[list[str], operator.add]  # appended: which stations the request passed
    route: Route  # overwritten: general or portfolio (Lab 23)
    status: Literal["received", "drafted", "revising", "answered"]  # overwritten
    answer: str  # overwritten: the latest answer
    revisions: int  # overwritten: how often the review sent the draft back (Lab 24)
    checked: bool  # overwritten: True when every figure was found in the tool results


def intake(state: ResearchState) -> dict:
    """Turn the request into the first messages for the model (no AI in this step)."""
    brief = f"Client {state['client_id']} ({state['client_profile']}): {state['question']}"
    return {
        "messages": [SystemMessage(RESEARCH_PROMPT), HumanMessage(brief)],
        "steps": ["intake"],
        "status": "received",
        "revisions": 0,
    }


def classify(state: ResearchState) -> dict:
    """Read the question and choose a track (rules only, no AI in this step)."""
    return {"route": classify_question(state["question"]), "steps": ["classify"]}


def pick_track(state: ResearchState) -> Route:
    """The switch after classify: it only reads the route that classify wrote."""
    return state["route"]


def is_source(message: BaseMessage) -> bool:
    """Tool results and the analyst's brief count as sources; review notes do not."""
    return message.type == "tool" or (message.type == "human" and message.name != "reviewer")


def after_review(state: ResearchState) -> Literal["revise", "done"]:
    """The switch after review: back to analyse, or on to the end."""
    return "revise" if state["status"] == "revising" else "done"


def build_research_graph(
    model: BaseChatModel, portfolio: PortfolioService, max_revisions: int = 2
) -> CompiledStateGraph:
    tools = build_portfolio_tools(portfolio)
    model_with_tools = model.bind_tools(tools)

    async def analyse(state: ResearchState) -> dict:
        """Reason: the model either asks for tools or writes a draft answer."""
        reply = await model_with_tools.ainvoke(state["messages"])
        update = {"messages": [reply], "steps": ["analyse"]}
        if not reply.tool_calls:
            update |= {"status": "drafted", "answer": str(reply.content)}
        return update

    def review(state: ResearchState) -> dict:
        """Check the draft: every figure must appear in the tool results or the brief."""
        sources = " ".join(str(m.content) for m in state["messages"] if is_source(m))
        unsupported = unsupported_figures(state["answer"], sources)
        if not unsupported:
            return {"steps": ["review"], "status": "answered", "checked": True}
        if state["revisions"] >= max_revisions:
            return {"steps": ["review"], "status": "answered", "checked": False}
        note = HumanMessage(
            "Revise your answer. These figures are not in the tool results: "
            f"{', '.join(unsupported)}. Quote only figures returned by the tools.",
            name="reviewer",
        )
        return {
            "messages": [note],
            "steps": ["review"],
            "status": "revising",
            "revisions": state["revisions"] + 1,
        }

    async def explain(state: ResearchState) -> dict:
        """Answer a general question directly: no tools, one model call."""
        reply = await model.ainvoke(state["messages"])
        return {
            "messages": [reply],
            "steps": ["explain"],
            "status": "answered",
            "answer": str(reply.content),
        }

    builder = StateGraph(ResearchState, input_schema=ResearchInput, output_schema=ResearchOutput)
    builder.add_node("intake", intake)
    builder.add_node("classify", classify)
    builder.add_node("analyse", analyse)
    builder.add_node("tools", ToolNode(tools))  # act: run the requested tools
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
