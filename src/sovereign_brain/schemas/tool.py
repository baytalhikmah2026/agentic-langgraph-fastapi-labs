"""How the API describes a tool (Lab 42)."""

from pydantic import BaseModel


class ToolInfo(BaseModel):
    """One tool on the wall: its name, what it does, and the JSON Schema of its form."""

    name: str
    description: str
    parameters: dict
