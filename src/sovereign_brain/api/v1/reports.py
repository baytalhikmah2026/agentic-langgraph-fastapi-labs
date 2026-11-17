"""Portfolio reports (Lab 49): a fixed protocol and a strict, validated JSON answer."""

import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from langgraph.graph.state import CompiledStateGraph

from sovereign_brain.api.v1.research import RunContext
from sovereign_brain.core.rate_limit import model_call_gate
from sovereign_brain.core.request_id import get_request_id
from sovereign_brain.core.security import get_current_user
from sovereign_brain.core.settings import get_settings
from sovereign_brain.db.repository import Clients
from sovereign_brain.schemas.report import ReportResponse, ResearchReport

router = APIRouter(
    prefix="/v1/reports", tags=["reports"], dependencies=[Depends(get_current_user)]
)
logger = logging.getLogger("sovereign_brain.report")


def get_report_graph(request: Request) -> CompiledStateGraph:
    """The report graph built once at start-up (see lifespan in main.py)."""
    return request.app.state.report_graph


ReportGraph = Annotated[CompiledStateGraph, Depends(get_report_graph)]


@router.post("/{client_id}", dependencies=[Depends(model_call_gate)])
async def create_report(
    client_id: Annotated[str, Path(pattern=r"^[Cc]-\d{4}$")],
    clients: Clients,
    graph: ReportGraph,
    context: RunContext,
) -> ReportResponse:
    """A portfolio report for one client, always in the ResearchReport shape."""
    client = await clients.get(client_id.upper())
    if client is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Client {client_id} not found")
    profile = f"{client.name}, {client.segment}, risk profile {client.risk_profile}"
    config = {
        "recursion_limit": get_settings().graph_recursion_limit,
        "metadata": {"request_id": get_request_id()},
    }
    result = await graph.ainvoke(
        {"client_id": client.id, "client_profile": profile}, config=config, context=context
    )
    logger.info(
        "Report for %s: %d drafts, checked=%s", client.id, result["attempts"], result["checked"]
    )
    return ReportResponse(
        request_id=get_request_id(),
        report=ResearchReport.model_validate(result["report"]),
        attempts=result["attempts"],
        checked=result["checked"],
        created_at=datetime.now(UTC),
    )
