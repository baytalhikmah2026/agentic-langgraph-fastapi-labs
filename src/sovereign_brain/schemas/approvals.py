"""Reports waiting for a person (Module 7): what the approval endpoints return."""

from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

from sovereign_brain.schemas.report import ResearchReport
from sovereign_brain.schemas.research import TrailStep

ApprovalState = Literal["awaiting_approval", "paused", "delivered", "rejected"]


class ApprovalStatus(BaseModel):
    """Where one approval run stands: waiting, paused, delivered, or rejected (Lab 63)."""

    approval_id: str
    client_id: str
    status: ApprovalState
    next: list[str]  # the station the run will go to when it is released
    report: ResearchReport | None
    checked: bool | None
    delivered: str | None
    feedback: list[str]  # reviewer notes the desk has received (Lab 64)
    overridden_by: str | None  # the desk lead who changed the run, if anyone (Lab 65)
    trail: list[TrailStep]


class ApprovalSummary(BaseModel):
    """One line of the approvals list (Lab 63)."""

    approval_id: str
    client_id: str
    requested_by: str
    requested_at: datetime


class Decision(BaseModel):
    """A person's decision about one waiting report (Lab 63)."""

    action: Literal["approve", "reject"]
    comment: str | None = Field(default=None, max_length=500)


class Feedback(BaseModel):
    """A reviewer's note for the desk: what to change in the next draft (Lab 64)."""

    comment: str = Field(min_length=3, max_length=500)


class Override(BaseModel):
    """A desk lead's override (Lab 65): their own report, or the plain fallback report."""

    mode: Literal["edit", "fallback"]
    report: ResearchReport | None = None  # the edited report, needed for "edit"
    reason: str = Field(min_length=3, max_length=500)

    @model_validator(mode="after")
    def edit_needs_a_report(self) -> Self:
        if self.mode == "edit" and self.report is None:
            raise ValueError("an edit needs the edited report")
        return self


class ApprovalRecord(BaseModel):
    """The approvals register row of one report (Lab 70)."""

    requested_by: str
    requested_at: datetime
    status: str
    decided_by: str | None
    decided_at: datetime | None
    comment: str | None


class HistoryStep(BaseModel):
    """One saved step of an approval run: what happened, caused by whom, in which trace."""

    step: int
    source: str  # "input" (a request), "loop" (a station ran) or "update" (a person's action)
    next: list[str]
    actor: str | None  # the signed-in person behind this step
    request_id: str | None
    trace_id: str | None  # open it in Jaeger (Lab 66), when tracing is on
    created_at: str


class ApprovalHistory(BaseModel):
    """The audit record of one report (Lab 70): where it stands, the register, every step."""

    approval: ApprovalStatus
    register: ApprovalRecord | None
    steps: list[HistoryStep]
