"""Research requests: the main counter of the Research Desk."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from langgraph.graph.state import CompiledStateGraph

from sovereign_brain.db.repository import Clients
from sovereign_brain.schemas.research import ResearchRequest, ResearchResponse

router = APIRouter(prefix="/v1/research", tags=["research"])


def get_research_graph(request: Request) -> CompiledStateGraph:
    """The graph built once at start-up (see lifespan in main.py)."""
    return request.app.state.research_graph


ResearchGraph = Annotated[CompiledStateGraph, Depends(get_research_graph)]


@router.post("")
async def submit_research(
    body: ResearchRequest, graph: ResearchGraph, clients: Clients
) -> ResearchResponse:
    client = await clients.get(body.client_id)
    if client is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Client {body.client_id} not found")
    profile = f"{client.name}, {client.segment}, risk profile {client.risk_profile}"
    result = await graph.ainvoke(
        {"client_id": body.client_id, "client_profile": profile, "question": body.question}
    )
    return ResearchResponse(
        request_id=uuid4().hex,
        client_id=body.client_id,
        status="completed",
        summary=result["answer"],
        created_at=datetime.now(UTC),
    )
