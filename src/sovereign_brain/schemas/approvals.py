"""Reports waiting for a person (Module 7): what the approval endpoints return."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

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
