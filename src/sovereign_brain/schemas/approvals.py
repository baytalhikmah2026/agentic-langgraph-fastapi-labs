"""Reports waiting for a person (Module 7): what the approval endpoints return."""

from typing import Literal

from pydantic import BaseModel

from sovereign_brain.schemas.report import ResearchReport
from sovereign_brain.schemas.research import TrailStep

ApprovalState = Literal["awaiting_approval", "paused", "delivered"]


class ApprovalStatus(BaseModel):
    """Where one approval run stands: waiting, paused at a checkpoint, or delivered."""

    approval_id: str
    client_id: str
    status: ApprovalState
    next: list[str]  # the station the run will go to when it is released
    report: ResearchReport | None
    checked: bool | None
    delivered: str | None
    trail: list[TrailStep]
