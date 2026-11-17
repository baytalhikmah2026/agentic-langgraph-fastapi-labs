"""The state bridge between graphs (Lab 54): what crosses from one graph to another.

The network (Lab 53) saves its work under its own namespace. Another graph never reads that
state directly: it receives a CaseFile, checked at the border like a passport. A case that is
incomplete, or has fields nobody agreed on, is turned back instead of travelling on.
"""

from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, ConfigDict, Field

from sovereign_brain.memory.shared_state import case_thread
from sovereign_brain.schemas.team import TeamNote


class CaseNotFound(LookupError):
    """No saved case with this ID for this analyst."""


class CaseFile(BaseModel):
    """A finished piece of team work, in the shape every other graph may rely on."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    client_id: str = Field(pattern=r"^C-\d{4}$")
    question: str = Field(min_length=5, max_length=500)
    notes: list[TeamNote] = Field(min_length=1)
    answer: str = Field(min_length=1)


async def export_case(network: CompiledStateGraph, owner: str, case_id: str) -> CaseFile:
    """Read the network's saved state for one case and pass it through the border check."""
    config = {"configurable": {"thread_id": case_thread("network", owner, case_id)}}
    snapshot = await network.aget_state(config)
    if not snapshot.values:
        raise CaseNotFound(case_id)
    values = snapshot.values
    return CaseFile(
        case_id=case_id,
        client_id=values["client_id"],
        question=values["question"],
        notes=values.get("notes", []),
        answer=values.get("answer", ""),
    )
