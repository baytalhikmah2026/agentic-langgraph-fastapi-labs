"""The events of the Autonomous Research Assistant (Lab 50): every step, in a checked shape.

The assistant streams what it does while it works. Each event is a Pydantic model, so a
dashboard can rely on its fields, and nothing leaves the API without being validated first.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

from sovereign_brain.schemas.report import ResearchReport


class PlanEvent(BaseModel):
    """The assistant's first decision: research a question, or write a report."""

    type: Literal["plan"] = "plan"
    mode: Literal["research", "report"]
    thread_id: str


class StepEvent(BaseModel):
    """A station of the graph finished and noted what it decided."""

    type: Literal["step"] = "step"
    station: str
    note: str


class ToolCallEvent(BaseModel):
    """The model asked for a tool, with these arguments."""

    type: Literal["tool_call"] = "tool_call"
    tool: str
    args: dict[str, Any]


class ToolResultEvent(BaseModel):
    """A tool answered (ok) or failed; the preview is cut short on purpose."""

    type: Literal["tool_result"] = "tool_result"
    tool: str
    ok: bool
    preview: str = Field(max_length=200)


class AnswerEvent(BaseModel):
    """The research answer at the end of a research run."""

    type: Literal["answer"] = "answer"
    summary: str
    route: Literal["general", "portfolio"]
    checked: bool | None


class ReportEvent(BaseModel):
    """The validated report at the end of a report run."""

    type: Literal["report"] = "report"
    report: ResearchReport
    checked: bool


AssistantEvent = PlanEvent | StepEvent | ToolCallEvent | ToolResultEvent | AnswerEvent | ReportEvent
