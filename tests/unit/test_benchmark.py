"""Benchmark helpers (Lab 59): counting tokens from callbacks, and the comparison table."""

from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, LLMResult

from sovereign_brain.services.benchmark import TokenCounter, TopologyRun, summary_table


def test_the_counter_adds_up_every_model_call() -> None:
    usage = {"input_tokens": 120, "output_tokens": 15, "total_tokens": 135}
    reply = LLMResult(generations=[[ChatGeneration(message=AIMessage("Hi", usage_metadata=usage))]])
    counter = TokenCounter()

    counter.on_llm_end(reply)
    counter.on_llm_end(reply)

    assert (counter.calls, counter.input_tokens, counter.output_tokens) == (2, 240, 30)


def test_the_table_lists_the_cheapest_shape_first() -> None:
    runs = [
        TopologyRun("supervisor", calls=10, input_tokens=9000, output_tokens=600, answers=2),
        TopologyRun("network", calls=6, input_tokens=5000, output_tokens=400, answers=2),
    ]

    lines = summary_table(runs).splitlines()

    assert lines[1].startswith("network")
    assert lines[1].endswith("2,700")  # (5,000 + 400) tokens / 2 answers
