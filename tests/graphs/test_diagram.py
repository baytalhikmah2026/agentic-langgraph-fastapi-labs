from collections.abc import Callable
from pathlib import Path

from sovereign_brain.graphs.diagram import diagram_document, mermaid
from sovereign_brain.graphs.research import build_research_graph

DOCUMENT = Path(__file__).parents[2] / "docs" / "research_graph.md"


def test_the_diagram_shows_every_station(make_model: Callable) -> None:
    text = mermaid(build_research_graph(make_model([])))

    for station in ["intake", "classify", "analyse", "tools", "explain", "review", "remember"]:
        assert f"\t{station}({station}" in text  # tools also lists its tool names
    assert "-." in text  # conditional edges are drawn dotted


def test_the_documentation_matches_the_code(make_model: Callable) -> None:
    expected = diagram_document(build_research_graph(make_model([])))

    assert DOCUMENT.read_text(encoding="utf-8") == expected, (
        "docs/research_graph.md is out of date: run "
        "uv run python scripts/export_graph_diagram.py"
    )
