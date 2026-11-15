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
    cached: bool = False
    created_at: datetime
