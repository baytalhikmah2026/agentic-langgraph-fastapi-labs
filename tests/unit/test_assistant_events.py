"""The assistant's plan and events (Lab 50): plain code, no model."""

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from sovereign_brain.api.v1.assistant import events_from_update, plan_mode
from sovereign_brain.graphs.trail import mark
from sovereign_brain.schemas.assistant import StepEvent, ToolCallEvent, ToolResultEvent


@pytest.mark.parametrize(
    ("question", "mode"),
    [
        ("What is the latest price of Gulf Petroleum?", "research"),
        ("Write a portfolio report for this client.", "report"),
        ("Which reporting rules apply to bonds?", "research"),  # "reporting" is not "report"
    ],
)
def test_the_assistant_plans_research_or_a_report(question: str, mode: str) -> None:
    assert plan_mode(question) == mode


def test_a_tool_request_becomes_a_step_and_a_tool_call() -> None:
    call = {"name": "get_quote", "args": {"ticker": "GLFP"}, "id": "call-1"}
    update = {
        "messages": [AIMessage("", tool_calls=[call])],
        "trail": mark("analyse", "Asked for tools: get_quote"),
    }

    assert events_from_update(update) == [
        StepEvent(station="analyse", note="Asked for tools: get_quote"),
        ToolCallEvent(tool="get_quote", args={"ticker": "GLFP"}),
    ]


def test_tool_results_say_whether_they_worked() -> None:
    mcp_result = ToolMessage(
        [{"type": "text", "text": '{"ticker": "GLFP", "price": 62.4}'}],
        tool_call_id="call-1",
        name="get_quote",
    )
    failed = ToolMessage("Tool error (ValueError): ...", tool_call_id="call-2",
                         name="stress_test", status="error")

    assert events_from_update({"messages": [mcp_result, failed]}) == [
        ToolResultEvent(tool="get_quote", ok=True, preview='{"ticker": "GLFP", "price": 62.4}'),
        ToolResultEvent(tool="stress_test", ok=False, preview="Tool error (ValueError): ..."),
    ]
