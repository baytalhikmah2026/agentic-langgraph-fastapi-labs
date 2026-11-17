"""What the team endpoints return (Module 6)."""

from datetime import datetime

from pydantic import BaseModel

from sovereign_brain.schemas.research import TrailStep


class TeamNote(BaseModel):
    author: str
    text: str


class TeamResponse(BaseModel):
    """The team's answer, its shared notebook and who did what."""

    request_id: str
    client_id: str
    summary: str
    notes: list[TeamNote]
    trail: list[TrailStep]
    created_at: datetime
