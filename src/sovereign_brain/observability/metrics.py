"""Metrics (Lab 68): numbers that add up over time, read by Prometheus from /metrics.

Traces (Lab 66) show one request. Metrics count everything: graph runs, how long each station
takes, model tokens, and what people decide about reports. MetricsRecorder, a LangChain
callback like GraphTracer, is registered once when this module is imported, so every graph
and model run in the process is counted.
"""

import time
from contextvars import ContextVar
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Response
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.tracers.context import register_configure_hook
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

GRAPH_RUNS = Counter(
    "sb_graph_runs", "Graph runs, by graph and outcome (ok or error)", ["graph", "outcome"]
)
STATION_SECONDS = Histogram(
    "sb_station_duration_seconds",
    "How long one station (graph node) takes",
    ["graph", "station"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1, 2.5, 5, 10, 20, 40, 80),
)
MODEL_SECONDS = Histogram(
    "sb_model_call_duration_seconds",
    "How long one model call takes",
    ["model"],
    buckets=(0.5, 1, 2.5, 5, 10, 20, 40, 80, 160),
)
MODEL_TOKENS = Counter(
    "sb_model_tokens", "Model tokens, by model and kind (input or output)", ["model", "kind"]
)
APPROVAL_ACTIONS = Counter(
    "sb_approval_actions",
    "What people did with waiting reports (approved, rejected, sent_back, override_edit ...)",
    ["action"],
)


class MetricsRecorder(BaseCallbackHandler):
    """Counts graph runs, times stations and model calls, and adds up tokens."""

    run_inline = True

    def __init__(self) -> None:
        self.parents: dict[UUID, UUID | None] = {}
        self.graphs: dict[UUID, str] = {}  # top-level run -> graph name
        self.started: dict[UUID, tuple[str, float]] = {}  # station or model run -> label, start

    def graph_of(self, run_id: UUID | None) -> str:
        while run_id is not None and run_id not in self.graphs:
            run_id = self.parents.get(run_id)
        return self.graphs.get(run_id, "none") if run_id is not None else "none"

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
        if parent_run_id is None:
            self.graphs[run_id] = name
        elif name == (metadata or {}).get("langgraph_node"):
            self.started[run_id] = (name, time.perf_counter())

    def finish_chain(self, run_id: UUID, outcome: str) -> None:
        if run_id in self.started:
            station, start = self.started.pop(run_id)
            graph = self.graph_of(run_id)
            STATION_SECONDS.labels(graph, station).observe(time.perf_counter() - start)
        if run_id in self.graphs:
            GRAPH_RUNS.labels(self.graphs.pop(run_id), outcome).inc()
        self.parents.pop(run_id, None)

    def on_chain_end(self, outputs: Any, *, run_id: UUID, **kwargs: Any) -> None:
        self.finish_chain(run_id, "ok")

    def on_chain_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        self.finish_chain(run_id, "error")

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
        model = (metadata or {}).get("ls_model_name", "unknown")
        self.started[run_id] = (model, time.perf_counter())

    def on_llm_end(self, response: LLMResult, *, run_id: UUID, **kwargs: Any) -> None:
        if run_id not in self.started:
            return
        model, start = self.started.pop(run_id)
        MODEL_SECONDS.labels(model).observe(time.perf_counter() - start)
        message = getattr(response.generations[0][0], "message", None)
        usage = getattr(message, "usage_metadata", None) or {}
        MODEL_TOKENS.labels(model, "input").inc(usage.get("input_tokens", 0))
        MODEL_TOKENS.labels(model, "output").inc(usage.get("output_tokens", 0))

    def on_llm_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        self.started.pop(run_id, None)


RECORDER = MetricsRecorder()
# Registered once per process: every LangChain/LangGraph run picks the recorder up
register_configure_hook(ContextVar("sb_metrics_recorder", default=RECORDER), inheritable=True)

router = APIRouter(tags=["metrics"])


@router.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    """Every metric in Prometheus' text format; Prometheus reads this page every 15 seconds."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
