"""Map-reduce (Lab 57): every piece read at the same time, collapsed when still too long."""

from collections.abc import Callable

from langchain_core.messages import AIMessage

from sovereign_brain.graphs.team.mapreduce import build_mapreduce_graph
from sovereign_brain.graphs.trail import stations

FOUR_PARAGRAPHS = "\n\n".join(f"Paragraph {n} of the markets review." for n in range(1, 5))
PART = "Part summary, short."  # 20 characters
DOC_INPUT = {"name": "review.md", "text": FOUR_PARAGRAPHS, "focus": "Energy risk"}


async def test_every_piece_is_read_and_reduced_in_one_round(make_model: Callable) -> None:
    model = make_model([AIMessage(PART)] * 4 + [AIMessage("The final summary.")])
    graph = build_mapreduce_graph(model, chunk_chars=40, collapse_chars=500)

    result = await graph.ainvoke(DOC_INPUT, output_keys=["summary", "chunks", "rounds", "trail"])

    assert (result["chunks"], result["rounds"]) == (4, 1)
    assert stations(result["trail"]) == ["split", "collect", "reduce"]
    assert result["summary"] == "The final summary."


async def test_summaries_that_are_still_too_long_are_collapsed(make_model: Callable) -> None:
    # Round 1: four summaries, 80 characters > 50, so they are grouped in pairs and read again
    model = make_model([AIMessage(PART)] * 6 + [AIMessage("The final summary.")])
    graph = build_mapreduce_graph(model, chunk_chars=40, collapse_chars=50)

    result = await graph.ainvoke(DOC_INPUT)

    assert result == {"summary": "The final summary.", "chunks": 4, "rounds": 2}
