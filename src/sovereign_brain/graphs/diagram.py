"""Diagrams of the graphs, generated from the code (Lab 27): never drawn by hand."""

from langgraph.graph.state import CompiledStateGraph


def mermaid(graph: CompiledStateGraph) -> str:
    """The graph as Mermaid text: stations, solid edges, dotted conditional edges."""
    return graph.get_graph().draw_mermaid()


def diagram_document(graph: CompiledStateGraph) -> str:
    """The Markdown page kept in docs/: a title, a note and the diagram in a mermaid block."""
    return (
        f"# The {graph.name} graph\n\n"
        "Generated from the code by `scripts/export_graph_diagram.py`. Do not edit by hand.\n\n"
        f"```mermaid\n{mermaid(graph)}```\n"
    )
