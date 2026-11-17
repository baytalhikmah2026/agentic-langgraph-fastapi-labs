"""How the API describes a tool (Labs 42, 44)."""

from typing import Literal

from pydantic import BaseModel


class ToolInfo(BaseModel):
    """One tool on the wall: its name, what it does, and the JSON Schema of its form."""

    name: str
    description: str
    parameters: dict
    source: Literal["local", "mcp"] = "local"  # our own code, or an MCP server (Lab 44)
