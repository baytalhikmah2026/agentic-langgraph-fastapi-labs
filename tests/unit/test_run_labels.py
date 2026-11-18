"""Run labels (Labs 67, 70): every approval run carries a tag, its approval_id, its actor."""

from opentelemetry.sdk.trace import TracerProvider

from sovereign_brain.api.v1.approvals import approval_config

APPROVAL_ID = "4b7e1c9a2d5f4e3b8a6c0d1e2f3a4b5c"


def test_an_approval_run_is_labelled() -> None:
    config = approval_config(APPROVAL_ID)

    assert config["tags"] == ["approvals"]
    assert config["metadata"]["approval_id"] == APPROVAL_ID
    assert config["configurable"]["thread_id"] == f"approval:{APPROVAL_ID}"


def test_the_actor_and_the_trace_are_saved_with_the_run() -> None:
    tracer = TracerProvider().get_tracer("test")

    without_trace = approval_config(APPROVAL_ID, actor="omar")
    with tracer.start_as_current_span("request") as span:
        with_trace = approval_config(APPROVAL_ID, actor="omar")

    assert without_trace["metadata"]["actor"] == "omar"
    assert "trace_id" not in without_trace["metadata"]  # tracing is off in tests
    assert with_trace["metadata"]["trace_id"] == format(span.get_span_context().trace_id, "032x")
