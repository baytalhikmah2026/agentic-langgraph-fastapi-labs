"""Lab 27: write the research graph's diagram to docs/research_graph.md.

Run it after every change to the graph. Nothing is contacted: the graph is only built.
"""

from pathlib import Path

from sovereign_brain.core.settings import get_settings
from sovereign_brain.graphs.diagram import diagram_document
from sovereign_brain.graphs.research import build_research_graph
from sovereign_brain.llm.factory import get_chat_model

TARGET = Path("docs/research_graph.md")


def main() -> None:
    graph = build_research_graph(get_chat_model(get_settings()))
    TARGET.parent.mkdir(exist_ok=True)
    TARGET.write_text(diagram_document(graph), encoding="utf-8", newline="\n")
    stations = [name for name in graph.get_graph().nodes if not name.startswith("__")]
    print(f"Wrote {TARGET} ({len(stations)} stations: {', '.join(stations)})")


if __name__ == "__main__":
    main()
