"""Tool errors as messages (Lab 43)."""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from sovereign_brain.tools.errors import error_reports, failed_tools, tool_error_message


def test_the_error_message_is_one_short_line_with_advice() -> None:
    error = ConnectionError("database\n   not reachable " + "x" * 1000)

    text = tool_error_message(error)

    assert text.startswith("Tool error (ConnectionError): database not reachable x")
    assert "\n" not in text
    assert text.endswith("or say which data is not available.")
    assert len(text) < 600


def error(content: str, call: str) -> ToolMessage:
    return ToolMessage(content, tool_call_id=call, name="stress_test", status="error")


def test_only_errors_of_the_current_question_count() -> None:
    messages = [
        HumanMessage("Question 1"),
        error("Tool error: old", "call-1"),
        AIMessage("Answer 1"),
        HumanMessage("Question 2"),
        error("Tool error: new", "call-2"),
        ToolMessage('{"percent": 18.5}', tool_call_id="call-3", name="sector_exposure"),
        HumanMessage("Revise your answer.", name="reviewer"),
    ]

    assert [m.content for m in failed_tools(messages)] == ["Tool error: new"]


def test_error_reports_list_only_the_failed_tools() -> None:
    messages = [
        error("Tool error: shock too large", "call-1"),
        ToolMessage('{"percent": 18.5}', tool_call_id="call-2", name="sector_exposure"),
    ]

    assert error_reports(messages) == [
        {"tool": "stress_test", "error": "Tool error: shock too large"}
    ]
