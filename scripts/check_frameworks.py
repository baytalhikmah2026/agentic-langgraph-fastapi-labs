"""Lab 6: show the installed framework versions and run a tiny graph that uses no AI model."""

from importlib.metadata import version
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from sovereign_brain.core.settings import get_settings
from sovereign_brain.llm.factory import get_chat_model

PACKAGES = ["fastapi", "pydantic", "langgraph", "langchain", "langchain-core", "langchain-ollama"]


class Ping(TypedDict):
    message: str


def pong(state: Ping) -> dict:
    return {"message": state["message"] + " -> pong"}


def main() -> None:
    for name in PACKAGES:
        print(f"{name:<17} {version(name)}")

    builder = StateGraph(Ping)
    builder.add_node("pong", pong)
    builder.add_edge(START, "pong")
    builder.add_edge("pong", END)
    graph = builder.compile()
    print("graph check:     ", graph.invoke({"message": "ping"})["message"])

    settings = get_settings()
    model = get_chat_model(settings)
    name = type(model).__name__
    print(f"chat model:       {name} '{settings.llm_model}' at {settings.ollama_base_url}")


if __name__ == "__main__":
    main()
