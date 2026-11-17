"""The software agency (Lab 60): one request in, one tested file out."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from sovereign_brain.schemas.research import TrailStep


class AgencyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    request: str = Field(min_length=10, max_length=500, description="What the team should build")


class AgencyResponse(BaseModel):
    """The outcome of one development cycle: the file, the verdict and how it got there."""

    request_id: str
    filename: str | None
    verdict: str
    rounds: int
    test_output: str
    trail: list[TrailStep]
    created_at: datetime
