"""Portfolio reports in a fixed shape (Lab 49): what other systems can rely on."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

RiskLevel = Literal["low", "medium", "high"]


class ResearchReport(BaseModel):
    """A portfolio report: the model fills in these fields and nothing else."""

    model_config = ConfigDict(extra="forbid")

    client_id: str = Field(pattern=r"^C-\d{4}$", description="The client ID from the brief")
    headline: str = Field(
        min_length=10, max_length=200, description="One sentence: the main finding, with a figure"
    )
    largest_sector: str = Field(
        min_length=2, max_length=40, description="The first sector in the facts"
    )
    largest_sector_percent: float = Field(
        ge=0, le=100, description="That sector's percent, as written in the facts"
    )
    risk_level: RiskLevel = Field(
        description="high if that percent is above 50, medium if above 25, otherwise low"
    )
    key_points: list[Annotated[str, Field(min_length=5, max_length=200)]] = Field(
        min_length=2,
        max_length=4,
        description="Two to four short facts, each with a figure from the facts",
    )


class ReportResponse(BaseModel):
    """What the report endpoint returns: always a valid report, and how it was made."""

    request_id: str
    report: ResearchReport
    attempts: int  # model drafts used (0 when the desk wrote the plain report itself)
    checked: bool  # True when a model draft matched the facts
    created_at: datetime
