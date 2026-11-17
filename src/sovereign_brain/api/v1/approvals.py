"""Reports that wait for a person (Module 7): the control tower of the Research Desk."""

import logging
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import StateSnapshot

from sovereign_brain.api.v1.research import RunContext
from sovereign_brain.core.rate_limit import model_call_gate
from sovereign_brain.core.request_id import get_request_id
from sovereign_brain.core.security import get_current_user
from sovereign_brain.core.settings import get_settings
from sovereign_brain.db.repository import Clients
from sovereign_brain.schemas.approvals import ApprovalStatus

router = APIRouter(
    prefix="/v1/approvals", tags=["approvals"], dependencies=[Depends(get_current_user)]
)
logger = logging.getLogger("sovereign_brain.approvals")
ApprovalId = Annotated[str, Path(pattern=r"^[0-9a-f]{32}$")]
ClientId = Annotated[str, Path(pattern=r"^[Cc]-\d{4}$")]


def get_approval_graph(request: Request) -> CompiledStateGraph:
    """The report graph with a deliver station and a pause before it (Lab 61)."""
    return request.app.state.approval_graph


ApprovalGraph = Annotated[CompiledStateGraph, Depends(get_approval_graph)]


def approval_config(approval_id: str) -> dict:
    """Every approval is its own thread in the checkpointer: "approval:<id>"."""
    return {
        "configurable": {"thread_id": f"approval:{approval_id}"},
        "recursion_limit": get_settings().graph_recursion_limit,
        "metadata": {"request_id": get_request_id()},
    }


def approval_status(approval_id: str, snapshot: StateSnapshot) -> ApprovalStatus:
    """Read the saved run: waiting before deliver, paused somewhere else, or delivered."""
    values = snapshot.values
    if "deliver" in snapshot.next:
        state = "awaiting_approval"
    elif snapshot.next:
        state = "paused"
    else:
        state = "delivered"
    return ApprovalStatus(
        approval_id=approval_id,
        client_id=values["client_id"],
        status=state,
        next=list(snapshot.next),
        report=values.get("report"),
        checked=values.get("checked"),
        delivered=values.get("delivered"),
        trail=values.get("trail", []),
    )


async def saved_status(approval_id: str, graph: CompiledStateGraph) -> ApprovalStatus:
    snapshot = await graph.aget_state(approval_config(approval_id))
    if not snapshot.values:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Approval {approval_id} not found")
    return approval_status(approval_id, snapshot)


@router.post("/reports/{client_id}", dependencies=[Depends(model_call_gate)])
async def request_report(
    client_id: ClientId, clients: Clients, graph: ApprovalGraph, context: RunContext
) -> ApprovalStatus:
    """Write a report and stop before it is sent: a person must release it."""
    client = await clients.get(client_id.upper())
    if client is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Client {client_id} not found")
    profile = f"{client.name}, {client.segment}, risk profile {client.risk_profile}"
    approval_id = uuid4().hex
    await graph.ainvoke(
        {"client_id": client.id, "client_profile": profile},
        config=approval_config(approval_id),
        context=context,
    )
    logger.info("Report for %s waits for approval %s", client.id, approval_id)
    return await saved_status(approval_id, graph)


@router.get("/{approval_id}")
async def get_approval(approval_id: ApprovalId, graph: ApprovalGraph) -> ApprovalStatus:
    """Where one approval stands, read from the checkpointer (it survives restarts)."""
    return await saved_status(approval_id, graph)
