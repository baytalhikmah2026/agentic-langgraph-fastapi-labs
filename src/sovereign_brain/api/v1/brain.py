"""The Brain's API (Lab 98): start a run, follow it live, decide at the pause, from any pod.

A run's state lives in the checkpointer (PostgreSQL in the cluster), keyed by its run ID, so a
run started on one API pod can be followed and approved on another.
"""

import logging
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.requests import HTTPConnection
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from pydantic import ValidationError

from sovereign_brain.api.v1.approvals import DeskSigner
from sovereign_brain.api.v1.research import get_portfolio
from sovereign_brain.capstone.graph import BrainContext
from sovereign_brain.capstone.schemas import BrainEvent, BrainRequest
from sovereign_brain.core.rate_limit import model_call_gate
from sovereign_brain.core.security import CurrentUser, user_from_token
from sovereign_brain.core.settings import get_settings
from sovereign_brain.db.repository import AuditLog, Users
from sovereign_brain.memory.threads import thread_config
from sovereign_brain.schemas.approvals import Decision
from sovereign_brain.security.rbac import allowed, require
from sovereign_brain.security.signing import report_hash
from sovereign_brain.services.portfolio import PortfolioService

router = APIRouter(prefix="/v1/brain", tags=["brain"])
logger = logging.getLogger("sovereign_brain.brain")
RunId = Annotated[str, Path(pattern=r"^[0-9a-f]{32}$")]
SPECIALISTS = {"supervisor", "extraction", "sanitization", "analysis"}
OUTCOMES = {"approve": "approved", "reject": "rejected"}


def get_brain_graph(connection: HTTPConnection) -> CompiledStateGraph:
    """The Brain built at start-up; works for HTTP requests and WebSockets alike."""
    return connection.app.state.brain_graph


BrainGraph = Annotated[CompiledStateGraph, Depends(get_brain_graph)]


Portfolio = Annotated[PortfolioService, Depends(get_portfolio)]


def brain_context(
    connection: HTTPConnection, portfolio: PortfolioService, analyst: str
) -> BrainContext:
    tools = {tool.name: tool for tool in connection.app.state.mcp_tools}  # Lab 44 tool wall
    return BrainContext(portfolio=portfolio, analyst=analyst, tools=tools)


def run_config(run_id: str) -> dict:
    return {
        **thread_config(f"brain:{run_id}"),
        "recursion_limit": get_settings().graph_recursion_limit,
    }


def event(kind: str, run_id: str, agent: str | None = None, **data: object) -> dict:
    """One BrainEvent, ready to send as JSON."""
    return BrainEvent(
        type=kind, run_id=run_id, agent=agent, data=data, at=datetime.now(UTC)
    ).model_dump(mode="json")


async def run_status(graph: CompiledStateGraph, run_id: str) -> dict:
    snapshot = await graph.aget_state(run_config(run_id))
    values = snapshot.values
    if not values:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Run {run_id} not found")
    if "decision" in values:
        state = "delivered" if values["decision"]["action"] == "approve" else "rejected"
    elif snapshot.next == ("approval",):
        state = "awaiting_approval"
    else:
        state = "unfinished"
    return {
        "run_id": run_id,
        "status": state,
        "requested_by": values["requested_by"],
        "steps": values.get("steps", []),
        "draft": values.get("draft"),
        "problems": values.get("problems", []),
    }


@router.post(
    "/runs",
    dependencies=[Depends(require("research:run")), Depends(model_call_gate)],
)
async def start_run(
    body: BrainRequest,
    user: CurrentUser,
    graph: BrainGraph,
    portfolio: Portfolio,
    connection: HTTPConnection,
) -> dict:
    """Run the team until the brief waits for a person (or the run ends)."""
    run_id = uuid4().hex
    start = {"request": body.model_dump(), "requested_by": user.username, "steps": []}
    await graph.ainvoke(
        start,
        config=run_config(run_id),
        context=brain_context(connection, portfolio, user.username),
    )
    return await run_status(graph, run_id)


@router.get("/runs/{run_id}", dependencies=[Depends(require("approvals:read"))])
async def get_run(run_id: RunId, graph: BrainGraph) -> dict:
    return await run_status(graph, run_id)


@router.post("/runs/{run_id}/decision", dependencies=[Depends(require("approvals:decide"))])
async def decide_run(
    run_id: RunId,
    decision: Decision,
    user: CurrentUser,
    graph: BrainGraph,
    audit: AuditLog,
    signer: DeskSigner,
    portfolio: Portfolio,
    connection: HTTPConnection,
) -> dict:
    """A second person releases or stops the brief; the decision is sealed into the log."""
    current = await run_status(graph, run_id)
    if current["status"] != "awaiting_approval":
        raise HTTPException(status.HTTP_409_CONFLICT, f"Run {run_id} is {current['status']}")
    if current["requested_by"] == user.username:  # four eyes (Lab 63)
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You may not decide on your own run")
    answer = {"action": decision.action, "by": user.username, "comment": decision.comment}
    await graph.ainvoke(
        Command(resume=answer),
        config=run_config(run_id),
        context=brain_context(connection, portfolio, current["requested_by"]),
    )
    statement = {
        "run_id": run_id,
        "decision": decision.action,
        "decided_by": user.username,
        "requested_by": current["requested_by"],
        "draft_sha256": report_hash(current["draft"]),
        "key_id": signer.key_id,
    }
    details = {**statement, "signature": signer.sign(statement)}
    outcome = OUTCOMES[decision.action]
    await audit.append(user.username, f"brain.{outcome}", run_id, details)  # DORA record
    logger.info("Brain run %s %s by %s", run_id, outcome, user.username)
    return await run_status(graph, run_id)


@router.websocket("/ws")
async def live_run(
    websocket: WebSocket,
    graph: BrainGraph,
    portfolio: Portfolio,
    users: Users,
    token: Annotated[str, Query()] = "",
) -> None:
    """Send one BrainRequest, then watch every step of the team until the pause."""
    await websocket.accept()
    try:  # browsers can't send an Authorization header on a WebSocket (Lab 99 improves this)
        user = await user_from_token(token, users.get)
    except HTTPException:
        user = None
    if user is None or not allowed(user.role, "research:run"):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    run_id = uuid4().hex
    try:
        request = BrainRequest.model_validate_json(await websocket.receive_text())
        await websocket.send_json(event("started", run_id, client_id=request.client_id))
        start = {"request": request.model_dump(), "requested_by": user.username, "steps": []}
        async for update in graph.astream(
            start,
            config=run_config(run_id),
            context=brain_context(websocket, portfolio, user.username),
            stream_mode="updates",
        ):
            for node, delta in update.items():
                if node == "__interrupt__":
                    await websocket.send_json(event("approval_needed", run_id, "supervisor"))
                elif node in SPECIALISTS and delta:
                    await websocket.send_json(event("agent", run_id, node, step=delta["steps"][-1]))
        await websocket.close()
    except ValidationError:
        await websocket.send_json(event("error", run_id, problem="The request is not valid"))
        await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
    except WebSocketDisconnect:
        logger.info("Brain run %s: the analyst left; the run's state is saved", run_id)
