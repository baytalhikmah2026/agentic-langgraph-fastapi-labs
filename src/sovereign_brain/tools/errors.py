"""When a tool fails (Lab 43): the error becomes a message the model can read and act on.

Without this, one failing tool stops the whole request. With it, the model sees what went
wrong, may fix its arguments and try again, and the graph stops after a set number of errors.
"""

from langchain_core.messages import AnyMessage, ToolMessage

ERROR_TEXT_LIMIT = 400  # characters of the error the model reads; enough to fix an argument


def tool_error_message(error: Exception) -> str:
    """What the model reads instead of a result: which error, what it said, what to do next."""
    details = " ".join(str(error).split())[:ERROR_TEXT_LIMIT]  # one line, not too long
    return (
        f"Tool error ({type(error).__name__}): {details} "
        "Read the tool's description, fix the arguments and call it again, "
        "or say which data is not available."
    )


def failed_tools(messages: list[AnyMessage]) -> list[ToolMessage]:
    """The tool results of the current question that are errors (earlier questions don't count)."""
    newest = max(i for i, m in enumerate(messages) if m.type == "human" and m.name != "reviewer")
    return [m for m in messages[newest:] if isinstance(m, ToolMessage) and m.status == "error"]


def error_reports(messages: list[AnyMessage]) -> list[dict]:
    """The errors among new tool results, in the shape the stream sends them."""
    return [
        {"tool": m.name, "error": str(m.content)}
        for m in messages
        if isinstance(m, ToolMessage) and m.status == "error"
    ]
