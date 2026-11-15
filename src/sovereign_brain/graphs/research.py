"""The Research Desk graph (Module 3): one graph that grows lab by lab.

Lab 21: a typed state with reducers, and two stations: intake and analyse.
Lab 22: analyse can call portfolio tools in a loop (the ReAct pattern).
Lab 23: classify picks a track: portfolio questions to analyse, general questions to explain.
"""

import operator
from typing import Annotated, Literal, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition

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


class ResearchState(TypedDict):
    """Everything the graph knows about one research request."""

    # Given by the API when the run starts
    client_id: str
    client_profile: str
    question: str
    # Written by the nodes
    messages: Annotated[list[AnyMessage], add_messages]  # appended: the talk with the model
    steps: Annotated[list[str], operator.add]  # appended: which stations the request passed
    route: Route  # overwritten: general or portfolio (Lab 23)
    status: Literal["received", "answered"]  # overwritten: where the request is now
    answer: str  # overwritten: the final answer


def intake(state: ResearchState) -> dict:
    """Turn the request into the first messages for the model (no AI in this step)."""
    brief = f"Client {state['client_id']} ({state['client_profile']}): {state['question']}"
    return {
        "messages": [SystemMessage(RESEARCH_PROMPT), HumanMessage(brief)],
        "steps": ["intake"],
        "status": "received",
    }


def classify(state: ResearchState) -> dict:
    """Read the question and choose a track (rules only, no AI in this step)."""
    return {"route": classify_question(state["question"]), "steps": ["classify"]}


def pick_track(state: ResearchState) -> Route:
    """The switch after classify: it only reads the route that classify wrote."""
    return state["route"]


def build_research_graph(model: BaseChatModel, portfolio: PortfolioService) -> CompiledStateGraph:
    tools = build_portfolio_tools(portfolio)
    model_with_tools = model.bind_tools(tools)

    async def analyse(state: ResearchState) -> dict:
        """Reason: the model either asks for tools or writes the final answer."""
        reply = await model_with_tools.ainvoke(state["messages"])
        update = {"messages": [reply], "steps": ["analyse"]}
        if not reply.tool_calls:
            update |= {"status": "answered", "answer": str(reply.content)}
        return update

    async def explain(state: ResearchState) -> dict:
        """Answer a general question directly: no tools, one model call."""
        reply = await model.ainvoke(state["messages"])
        return {
            "messages": [reply],
            "steps": ["explain"],
            "status": "answered",
            "answer": str(reply.content),
        }

    builder = StateGraph(ResearchState)
    builder.add_node("intake", intake)
    builder.add_node("classify", classify)
    builder.add_node("analyse", analyse)
    builder.add_node("tools", ToolNode(tools))  # act: run the requested tools
    builder.add_node("explain", explain)
    builder.add_edge(START, "intake")
    builder.add_edge("intake", "classify")
    builder.add_conditional_edges(
        "classify", pick_track, {"portfolio": "analyse", "general": "explain"}
    )
    builder.add_conditional_edges("analyse", tools_condition)  # tools, or END when done
    builder.add_edge("tools", "analyse")  # observe: the results go back to the model
    builder.add_edge("explain", END)
    return builder.compile(name="research")
