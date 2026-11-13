"""Lab 8: the first Research Desk graph. A plain step prepares the brief, the model answers it."""

from typing import TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

SYSTEM_PROMPT = (
    "You are an analyst on the Research Desk of Crescent Ledger Bank. "
    "Answer in at most three sentences. "
    "If you do not have the client's data, say which data you would check."
)


class HelloState(TypedDict, total=False):
    client_id: str
    question: str
    brief: str
    answer: str


def prepare_brief(state: HelloState) -> dict:
    """A plain Python step: no AI, just a clean, predictable brief."""
    return {"brief": f"Client {state['client_id']}: {state['question']}"}


def build_hello_graph(model: BaseChatModel) -> CompiledStateGraph:
    def answer(state: HelloState) -> dict:
        reply = model.invoke([SystemMessage(SYSTEM_PROMPT), HumanMessage(state["brief"])])
        return {"answer": str(reply.content)}

    builder = StateGraph(HelloState)
    builder.add_node("prepare_brief", prepare_brief)
    builder.add_node("answer", answer)
    builder.add_edge(START, "prepare_brief")
    builder.add_edge("prepare_brief", "answer")
    builder.add_edge("answer", END)
    return builder.compile(name="hello")
