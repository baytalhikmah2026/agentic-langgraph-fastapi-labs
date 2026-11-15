"""Look inside the graphs that run behind the Research Desk."""

from fastapi import APIRouter, Depends

from sovereign_brain.api.v1.research import ResearchGraph
from sovereign_brain.core.security import get_current_user
from sovereign_brain.graphs.introspection import describe_fields
from sovereign_brain.graphs.research import ResearchState

router = APIRouter(prefix="/v1/graphs", tags=["graphs"], dependencies=[Depends(get_current_user)])


@router.get("/research/state")
async def research_state(graph: ResearchGraph) -> dict:
    """The research graph's stations and how each state field is updated."""
    nodes = [name for name in graph.get_graph().nodes if not name.startswith("__")]
    return {"graph": graph.name, "nodes": nodes, "fields": describe_fields(ResearchState)}


@router.get("/research/schema")
async def research_schema(graph: ResearchGraph) -> dict:
    """The research graph's contract: what it accepts and what it returns (JSON Schema)."""
    return {"input": graph.get_input_jsonschema(), "output": graph.get_output_jsonschema()}
