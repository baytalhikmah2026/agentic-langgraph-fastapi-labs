"""Metrics (Lab 68): graph runs, stations and tokens are counted for Prometheus."""

from uuid import uuid4

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, LLMResult
from prometheus_client import REGISTRY

from sovereign_brain.graphs.hello import build_hello_graph
from sovereign_brain.observability.metrics import MetricsRecorder


def sample(name: str, **labels: str) -> float:
    """The current value of one metric (0 if it has never been counted)."""
    return REGISTRY.get_sample_value(name, labels) or 0.0


async def test_every_graph_run_is_counted() -> None:
    runs = sample("sb_graph_runs_total", graph="hello", outcome="ok")
    answers = sample("sb_station_duration_seconds_count", graph="hello", station="answer")
    model = GenericFakeChatModel(messages=iter([AIMessage("Energy is 12% of the portfolio.")]))

    # No callbacks passed: the recorder joins every run by itself
    await build_hello_graph(model).ainvoke({"client_id": "C-1042", "question": "Energy?"})

    assert sample("sb_graph_runs_total", graph="hello", outcome="ok") == runs + 1
    assert (
        sample("sb_station_duration_seconds_count", graph="hello", station="answer")
        == answers + 1
    )


def test_model_tokens_are_added_up() -> None:
    recorder = MetricsRecorder()
    run_id = uuid4()
    before = sample("sb_model_tokens_total", model="test-model", kind="input")
    usage = {"input_tokens": 612, "output_tokens": 141, "total_tokens": 753}
    reply = LLMResult(generations=[[ChatGeneration(message=AIMessage("ok", usage_metadata=usage))]])

    recorder.on_chat_model_start({}, [[]], run_id=run_id, metadata={"ls_model_name": "test-model"})
    recorder.on_llm_end(reply, run_id=run_id)

    assert sample("sb_model_tokens_total", model="test-model", kind="input") == before + 612
    assert recorder.started == {}
