"""End-to-end tracing (Lab 66): one request, one trace, from the API to the model and back.

The FastAPI instrumentation opens a span for every request. GraphTracer, a LangChain callback,
adds a child span for every graph run, every station and every model call. The spans travel
to the OpenTelemetry Collector, which passes them on to Jaeger.
"""

import logging
from contextvars import ContextVar
from typing import Any
from uuid import UUID

from fastapi import FastAPI
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.tracers.context import register_configure_hook
from opentelemetry import context as otel_context
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span, Status, StatusCode, Tracer

from sovereign_brain import __version__
from sovereign_brain.core.settings import Settings

logger = logging.getLogger("sovereign_brain.tracing")


class GraphTracer(BaseCallbackHandler):
    """Turns graph runs, stations and model calls into OpenTelemetry spans."""

    run_inline = True  # called in order, inside the run's own context

    def __init__(self, tracer: Tracer) -> None:
        self.tracer = tracer
        self.spans: dict[UUID, Span] = {}
        self.parents: dict[UUID, UUID | None] = {}

    def parent_context(self, parent_run_id: UUID | None) -> otel_context.Context:
        """The nearest traced ancestor; a top-level run hangs under the current request span."""
        while parent_run_id is not None:
            if parent_run_id in self.spans:
                return trace.set_span_in_context(self.spans[parent_run_id])
            parent_run_id = self.parents.get(parent_run_id)
        return otel_context.get_current()

    def start(self, name: str, run_id: UUID, parent_run_id: UUID | None, **attrs: str) -> None:
        context = self.parent_context(parent_run_id)
        self.spans[run_id] = self.tracer.start_span(name, context=context, attributes=attrs)

    def end(self, run_id: UUID, error: BaseException | None = None) -> None:
        self.parents.pop(run_id, None)
        span = self.spans.pop(run_id, None)
        if span is None:
            return
        if error is not None:
            span.record_exception(error)
            span.set_status(Status(StatusCode.ERROR, type(error).__name__))
        span.end()

    def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        self.parents[run_id] = parent_run_id
        name = kwargs.get("name") or "unnamed"
        station = (metadata or {}).get("langgraph_node")
        if parent_run_id is None:  # the graph run itself
            self.start(f"graph {name}", run_id, None, **{"langgraph.graph": name})
        elif name == station:  # one station (node); its inner steps are not traced
            self.start(f"station {name}", run_id, parent_run_id, **{"langgraph.node": name})

    def on_chain_end(self, outputs: Any, *, run_id: UUID, **kwargs: Any) -> None:
        self.end(run_id)

    def on_chain_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        self.end(run_id, error)

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[Any]],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        self.parents[run_id] = parent_run_id
        model = (metadata or {}).get("ls_model_name", "unknown")
        provider = (metadata or {}).get("ls_provider", "unknown")
        attrs = {"gen_ai.request.model": model, "gen_ai.provider.name": provider}
        self.start(f"chat {model}", run_id, parent_run_id, **attrs)

    def on_llm_end(self, response: LLMResult, *, run_id: UUID, **kwargs: Any) -> None:
        span = self.spans.get(run_id)
        message = getattr(response.generations[0][0], "message", None) if span else None
        usage = getattr(message, "usage_metadata", None) or {}
        if span is not None and usage:
            span.set_attribute("gen_ai.usage.input_tokens", usage.get("input_tokens", 0))
            span.set_attribute("gen_ai.usage.output_tokens", usage.get("output_tokens", 0))
        self.end(run_id)

    def on_llm_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        self.end(run_id, error)


def setup_tracing(app: FastAPI, settings: Settings) -> TracerProvider | None:
    """Switch tracing on when SB_OTEL_ENABLED is true (in Compose); otherwise do nothing."""
    if not settings.otel_enabled:
        return None
    resource = Resource.create(
        {"service.name": settings.otel_service_name, "service.version": __version__}
    )
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=f"{settings.otel_endpoint}/v1/traces")
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    # Health checks and Prometheus visits come every few seconds: no traces for them
    FastAPIInstrumentor.instrument_app(
        app, tracer_provider=provider, excluded_urls="health,metrics"
    )
    # Every LangChain/LangGraph run in this process picks up the tracer through this hook
    tracer = GraphTracer(provider.get_tracer("sovereign_brain.graphs"))
    register_configure_hook(ContextVar("sb_graph_tracer", default=tracer), inheritable=True)
    logger.info("Tracing on: spans go to %s", settings.otel_endpoint)
    return provider
