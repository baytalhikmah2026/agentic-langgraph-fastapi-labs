"""The shape of a research request and of the answer the Research Desk sends back."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ResearchRequest(BaseModel):
    """What an analyst sends to the Research Desk."""

    model_config = ConfigDict(strict=True, extra="forbid", str_strip_whitespace=True)

    client_id: str = Field(pattern=r"^C-\d{4}$", examples=["C-1042"])
    question: str = Field(min_length=10, max_length=2000)
    priority: Literal["normal", "urgent"] = "normal"
    max_sources: int = Field(default=3, ge=1, le=10)
    # Continue a conversation (Lab 31); leave it out to start a new one
    thread_id: str | None = Field(
        default=None, pattern=r"^[A-Za-z0-9-]{1,64}$", examples=["energy-review"]
    )

    @field_validator("client_id", mode="before")
    @classmethod
    def upper_case_client_id(cls, value: object) -> object:
        return value.upper() if isinstance(value, str) else value


class ResearchResponse(BaseModel):
    """What the Research Desk answers."""

    request_id: str
    client_id: str
    status: Literal["accepted", "completed"]
    summary: str | None = None
    route: Literal["general", "portfolio"] | None = None  # the track the graph took (Lab 25)
    checked: bool | None = None  # portfolio answers: were all figures found? (Lab 25)
    thread_id: str | None = None  # send it back to ask a follow-up (Lab 31)
    cached: bool = False
    created_at: datetime


class TrailStep(BaseModel):
    """One entry of the audit trail: a station, what it decided, and when."""

    node: str
    note: str
    at: datetime


class ResearchTrace(BaseModel):
    """A research answer together with its full audit trail (Lab 26)."""

    request_id: str
    client_id: str
    summary: str
    route: Literal["general", "portfolio"]
    checked: bool | None = None
    thread_id: str
    trail: list[TrailStep]
    created_at: datetime


class ResearchJob(BaseModel):
    """A queued research request and, once a worker has finished it, its answer (Lab 83)."""

    job_id: str
    status: Literal["queued", "running", "completed", "failed"]
    client_id: str
    thread_id: str
    summary: str | None = None
    route: Literal["general", "portfolio"] | None = None
    error: str | None = None
