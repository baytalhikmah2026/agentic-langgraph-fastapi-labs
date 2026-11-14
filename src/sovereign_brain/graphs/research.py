"""The Research Desk graph (Module 3): one graph that grows lab by lab.

Lab 21: a typed state with reducers, and two stations: intake and analyse.
"""

import operator
from typing import Annotated, Literal, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph

RESEARCH_PROMPT = (
    "You are an analyst on the Research Desk of Crescent Ledger Bank. "
    "Answer in at most three sentences. "
    "If you do not have the client's data, say which data you would check."
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


def build_research_graph(model: BaseChatModel) -> CompiledStateGraph:
    async def analyse(state: ResearchState) -> dict:
        reply = await model.ainvoke(state["messages"])
        return {
            "messages": [reply],
            "steps": ["analyse"],
            "status": "answered",
            "answer": str(reply.content),
        }

    builder = StateGraph(ResearchState)
    builder.add_node("intake", intake)
    builder.add_node("analyse", analyse)
    builder.add_edge(START, "intake")
    builder.add_edge("intake", "analyse")
    builder.add_edge("analyse", END)
    return builder.compile(name="research")
