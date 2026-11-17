"""Benchmarking team shapes (Lab 59): model calls, tokens and time for the same questions.

A TokenCounter is a LangChain callback. Passed in a run's config, it is called after every
model call inside the graph, however deep, and adds up the token counts the model reports.
"""

import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langgraph.graph.state import CompiledStateGraph

from sovereign_brain.graphs.context import ResearchContext


class TokenCounter(BaseCallbackHandler):
    """Counts model calls and the tokens each call reports (usage_metadata)."""

    def __init__(self) -> None:
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        self.calls += 1
        for generations in response.generations:
            for generation in generations:
                message = getattr(generation, "message", None)
                usage = getattr(message, "usage_metadata", None) or {}
                self.input_tokens += usage.get("input_tokens", 0)
                self.output_tokens += usage.get("output_tokens", 0)


@dataclass
class TopologyRun:
    """What one team shape spent on one or more questions."""

    name: str
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    seconds: float = 0.0
    answers: int = 0

    @property
    def tokens_per_answer(self) -> int:
        return (self.input_tokens + self.output_tokens) // max(self.answers, 1)


async def measure(
    run: TopologyRun,
    graph: CompiledStateGraph,
    graph_input: dict,
    context: ResearchContext,
    recursion_limit: int = 25,
) -> TopologyRun:
    """Run the graph once and add what it spent to `run`."""
    counter = TokenCounter()
    config = {"callbacks": [counter], "recursion_limit": recursion_limit}
    started = time.perf_counter()
    result = await graph.ainvoke(graph_input, config=config, context=context)
    run.seconds += time.perf_counter() - started
    run.calls += counter.calls
    run.input_tokens += counter.input_tokens
    run.output_tokens += counter.output_tokens
    run.answers += 1 if result.get("answer") else 0
    return run


def summary_table(runs: Sequence[TopologyRun]) -> str:
    """A plain-text table, cheapest team shape (tokens per answer) first."""
    lines = [
        f"{'Topology':<12}{'Calls':>7}{'Tokens in':>11}{'Tokens out':>12}"
        f"{'Seconds':>9}{'Tokens/answer':>15}"
    ]
    for run in sorted(runs, key=lambda r: r.tokens_per_answer):
        lines.append(
            f"{run.name:<12}{run.calls:>7}{run.input_tokens:>11,}{run.output_tokens:>12,}"
            f"{run.seconds:>9.1f}{run.tokens_per_answer:>15,}"
        )
    return "\n".join(lines)
