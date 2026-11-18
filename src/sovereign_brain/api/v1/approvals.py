"""Reports that wait for a person (Module 7): the control tower of the Research Desk."""

import logging
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import StateSnapshot

from sovereign_brain.api.v1.research import RunContext
from sovereign_brain.core.rate_limit import model_call_gate
from sovereign_brain.core.request_id import get_request_id
from sovereign_brain.core.security import CurrentUser, get_current_user
from sovereign_brain.core.settings import get_settings
from sovereign_brain.db.models import Approval, User
from sovereign_brain.db.repository import Approvals, Clients
from sovereign_brain.graphs.report import report_problems
from sovereign_brain.graphs.trail import mark
from sovereign_brain.schemas.approvals import (
    ApprovalStatus,
    ApprovalSummary,
    Decision,
    Feedback,
    Override,
)

router = APIRouter(
    prefix="/v1/approvals", tags=["approvals"], dependencies=[Depends(get_current_user)]
)
logger = logging.getLogger("sovereign_brain.approvals")
ApprovalId = Annotated[str, Path(pattern=r"^[0-9a-f]{32}$")]
ClientId = Annotated[str, Path(pattern=r"^[Cc]-\d{4}$")]
# Lab 62: optional extra pause right after a station, chosen per request
Inspect = Annotated[Literal["draft"] | None, Query(description="Pause after this station")]


def get_approval_graph(request: Request) -> CompiledStateGraph:
    """The report graph with a deliver station and a pause before it (Lab 61)."""
    return request.app.state.approval_graph


ApprovalGraph = Annotated[CompiledStateGraph, Depends(get_approval_graph)]


def approval_config(approval_id: str) -> dict:
    """Every approval is its own thread in the checkpointer: "approval:<id>".

    Lab 67: the tag and the approval_id label each run, so trace viewers (LangSmith, Jaeger)
    can filter all the runs of one approval.
    """
    return {
        "configurable": {"thread_id": f"approval:{approval_id}"},
        "recursion_limit": get_settings().graph_recursion_limit,
        "tags": ["approvals"],
        "metadata": {"request_id": get_request_id(), "approval_id": approval_id},
    }


def approval_status(approval_id: str, snapshot: StateSnapshot) -> ApprovalStatus:
    """Read the saved run: waiting before deliver, paused somewhere else, delivered or rejected."""
    values = snapshot.values
    if "deliver" in snapshot.next:
        state = "awaiting_approval"
    elif snapshot.next:
        state = "paused"
    elif values.get("delivered"):
        state = "delivered"
    else:
        state = "rejected"  # finished without a delivery (Lab 63)
    return ApprovalStatus(
        approval_id=approval_id,
        client_id=values["client_id"],
        status=state,
        next=list(snapshot.next),
        report=values.get("report"),
        checked=values.get("checked"),
        delivered=values.get("delivered"),
        feedback=values.get("feedback", []),
        overridden_by=values.get("overridden_by"),
        trail=values.get("trail", []),
    )


async def saved_status(approval_id: str, graph: CompiledStateGraph) -> ApprovalStatus:
    snapshot = await graph.aget_state(approval_config(approval_id))
    if not snapshot.values:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Approval {approval_id} not found")
    return approval_status(approval_id, snapshot)


@router.post("/reports/{client_id}", dependencies=[Depends(model_call_gate)])
async def request_report(
    client_id: ClientId,
    clients: Clients,
    approvals: Approvals,
    user: CurrentUser,
    graph: ApprovalGraph,
    context: RunContext,
    inspect: Inspect = None,
) -> ApprovalStatus:
    """Write a report and stop before it is sent: a person must release it.

    Lab 62: with ?inspect=draft the run also stops right after the first draft, so a person can
    look at what the model wrote before the guardrail checks it.
    Lab 63: the request is written into the approvals register, with who asked for it.
    """
    client = await clients.get(client_id.upper())
    if client is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Client {client_id} not found")
    profile = f"{client.name}, {client.segment}, risk profile {client.risk_profile}"
    approval_id = uuid4().hex
    await graph.ainvoke(
        {"client_id": client.id, "client_profile": profile},
        config=approval_config(approval_id),
        context=context,
        interrupt_after=[inspect] if inspect else None,  # only for this run (Lab 62)
    )
    await approvals.add(approval_id, client.id, requested_by=user.username)
    logger.info("Report for %s waits for approval %s", client.id, approval_id)
    return await saved_status(approval_id, graph)


@router.get("")
async def list_waiting(approvals: Approvals) -> list[ApprovalSummary]:
    """Every report still waiting for a decision, oldest first (Lab 63)."""
    return [
        ApprovalSummary(
            approval_id=record.id,
            client_id=record.client_id,
            requested_by=record.requested_by,
            requested_at=record.requested_at,
        )
        for record in await approvals.waiting()
    ]


@router.get("/{approval_id}")
async def get_approval(approval_id: ApprovalId, graph: ApprovalGraph) -> ApprovalStatus:
    """Where one approval stands, read from the checkpointer (it survives restarts)."""
    return await saved_status(approval_id, graph)


@router.post("/{approval_id}/continue", dependencies=[Depends(model_call_gate)])
async def continue_run(
    approval_id: ApprovalId, graph: ApprovalGraph, context: RunContext
) -> ApprovalStatus:
    """Let a run that paused for inspection carry on to its next hold line (Lab 62)."""
    current = await saved_status(approval_id, graph)
    if current.status != "paused":
        detail = f"Approval {approval_id} is {current.status}; only a paused run can continue"
        raise HTTPException(status.HTTP_409_CONFLICT, detail)
    await graph.ainvoke(None, config=approval_config(approval_id), context=context)
    return await saved_status(approval_id, graph)


async def waiting_record(
    approval_id: str, user: User, approvals: Approvals, graph: CompiledStateGraph
) -> Approval:
    """The gates of every decision (Labs 63-65): registered, waiting, and not your own."""
    current = await saved_status(approval_id, graph)
    record = await approvals.get(approval_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Approval {approval_id} is not registered")
    if current.status != "awaiting_approval":
        detail = f"Approval {approval_id} is {current.status}; only a waiting report can be decided"
        raise HTTPException(status.HTTP_409_CONFLICT, detail)
    if record.requested_by == user.username:  # the four-eyes rule
        detail = "You requested this report; a second person must decide"
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail)
    if current.overridden_by == user.username:  # nobody clears their own changes (Lab 65)
        detail = "You changed this report; another person must decide"
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail)
    return record


@router.post("/{approval_id}/decision")
async def decide(
    approval_id: ApprovalId,
    decision: Decision,
    user: CurrentUser,
    approvals: Approvals,
    graph: ApprovalGraph,
    context: RunContext,
) -> ApprovalStatus:
    """Approve (the report is delivered) or reject (it is never sent), by a second person."""
    record = await waiting_record(approval_id, user, approvals, graph)
    config = approval_config(approval_id)
    if decision.action == "approve":
        await graph.ainvoke(None, config=config, context=context)  # runs deliver
    else:
        note = f"Rejected by {user.username}: {decision.comment or 'no comment'}"
        # Record the rejection as if deliver had run: the run ends, and nothing is sent
        await graph.aupdate_state(config, {"trail": mark("deliver", note)}, as_node="deliver")
    outcome = "approved" if decision.action == "approve" else "rejected"
    await approvals.decide(record, outcome, decided_by=user.username, comment=decision.comment)
    logger.info("Approval %s %s by %s", approval_id, outcome, user.username)
    return await saved_status(approval_id, graph)


@router.post("/{approval_id}/feedback", dependencies=[Depends(model_call_gate)])
async def send_back(
    approval_id: ApprovalId,
    feedback: Feedback,
    user: CurrentUser,
    approvals: Approvals,
    graph: ApprovalGraph,
    context: RunContext,
) -> ApprovalStatus:
    """Send a waiting report back with a reviewer's note; a new draft returns for approval."""
    await waiting_record(approval_id, user, approvals, graph)
    config = approval_config(approval_id)
    note = f"{user.username}: {feedback.comment}"
    trail = mark("check", f"Sent back by {note}")
    update = {"feedback": [note], "verdict": "retry", "trail": trail}
    # Written as if the guardrail had sent the draft back: the run's next station is draft
    await graph.aupdate_state(config, update, as_node="check")
    await graph.ainvoke(None, config=config, context=context)  # new draft, check, hold line
    logger.info("Approval %s sent back by %s", approval_id, user.username)
    return await saved_status(approval_id, graph)


@router.post("/{approval_id}/override")
async def override(
    approval_id: ApprovalId,
    change: Override,
    user: CurrentUser,
    approvals: Approvals,
    graph: ApprovalGraph,
    context: RunContext,
) -> ApprovalStatus:
    """A desk lead changes the run's course: their own report, or the plain fallback (Lab 65)."""
    if user.role != "lead":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only a desk lead can override a report")
    await waiting_record(approval_id, user, approvals, graph)
    config = approval_config(approval_id)
    note = f"Overridden by {user.username} ({change.mode}): {change.reason}"
    update = {"overridden_by": user.username, "trail": mark("check", note)}
    if change.mode == "edit":
        facts = (await graph.aget_state(config)).values["facts"]
        problems = report_problems(change.report, facts)  # the same rules as for the model
        if problems:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, problems)
        update |= {"report": change.report.model_dump(), "checked": True, "verdict": "done"}
    else:
        update |= {"verdict": "fallback"}
    # Written as check: its verdict is the switch on the tracks (done -> deliver, fallback)
    await graph.aupdate_state(config, update, as_node="check")
    if change.mode == "fallback":
        await graph.ainvoke(None, config=config, context=context)  # fallback, then hold line
    logger.info("Approval %s overridden by %s (%s)", approval_id, user.username, change.mode)
    return await saved_status(approval_id, graph)
