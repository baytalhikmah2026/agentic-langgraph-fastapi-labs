"""Tracing (Lab 66): a graph run, its stations and its model call become one tree of spans."""

from fastapi import FastAPI
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from sovereign_brain.core.settings import Settings
from sovereign_brain.graphs.hello import build_hello_graph
from sovereign_brain.observability.tracing import GraphTracer, setup_tracing

QUESTION = {"client_id": "C-1042", "question": "Energy exposure?"}


async def test_a_graph_run_becomes_a_tree_of_spans() -> None:
    exporter = InMemorySpanExporter()  # keeps finished spans in a list, instead of sending them
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = GraphTracer(provider.get_tracer("test"))
    model = GenericFakeChatModel(messages=iter([AIMessage("Energy is 12% of the portfolio.")]))

    await build_hello_graph(model).ainvoke(QUESTION, config={"callbacks": [tracer]})

    spans = {span.name: span for span in exporter.get_finished_spans()}
    graph = spans["graph hello"]
    answer = spans["station answer"]
    chat = next(span for name, span in spans.items() if name.startswith("chat "))
    assert spans["station prepare_brief"].parent.span_id == graph.context.span_id
    assert answer.parent.span_id == graph.context.span_id
    assert chat.parent.span_id == answer.context.span_id  # the model call sits in its station
    assert tracer.spans == {}  # every span was ended


def test_tracing_is_off_unless_switched_on() -> None:
    assert setup_tracing(FastAPI(), Settings(otel_enabled=False)) is None
