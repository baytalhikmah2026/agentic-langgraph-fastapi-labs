"""Document analysis (Lab 57): what the analyst sends and what comes back."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    focus: str = Field(min_length=5, max_length=300, description="What the analyst looks for")


class DocumentAnalysis(BaseModel):
    """The final summary, with how many pieces were read and in how many rounds."""

    request_id: str
    name: str
    summary: str
    chunks: int
    rounds: int
    created_at: datetime
