"""Research requests: the main counter of the Research Desk."""

import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from langgraph.graph.state import CompiledStateGraph

from sovereign_brain.core.request_id import get_request_id
from sovereign_brain.core.settings import get_settings
from sovereign_brain.db.repository import Clients
from sovereign_brain.schemas.research import ResearchRequest, ResearchResponse

router = APIRouter(prefix="/v1/research", tags=["research"])
logger = logging.getLogger("sovereign_brain.research")


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
    request_id = get_request_id()
    logger.info("Research started for %s", body.client_id)
    result = await graph.ainvoke(
        {"client_id": body.client_id, "client_profile": profile, "question": body.question},
        config={
            "recursion_limit": get_settings().graph_recursion_limit,
            "metadata": {"request_id": request_id},
        },
    )
    logger.info("Research finished for %s", body.client_id)
    return ResearchResponse(
        request_id=request_id,
        client_id=body.client_id,
        status="completed",
        summary=result["answer"],
        created_at=datetime.now(UTC),
    )
