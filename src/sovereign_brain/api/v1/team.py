"""The Research Desk team (Module 6): requests answered by several agents together."""

import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from fastapi.sse import EventSourceResponse, ServerSentEvent
from langgraph.graph.state import CompiledStateGraph

from sovereign_brain.api.v1.research import Checked, RunContext
from sovereign_brain.core.errors import MODEL_ERRORS
from sovereign_brain.core.rate_limit import model_call_gate
from sovereign_brain.core.request_id import get_request_id
from sovereign_brain.core.security import get_current_user
from sovereign_brain.core.settings import get_settings
from sovereign_brain.memory.shared_state import case_thread
from sovereign_brain.schemas.team import TeamResponse

router = APIRouter(prefix="/v1/team", tags=["team"], dependencies=[Depends(get_current_user)])
logger = logging.getLogger("sovereign_brain.team")
# The output fields plus the trail: who did what, in order
TEAM_KEYS = ["answer", "notes", "trail"]


def get_team_graph(request: Request) -> CompiledStateGraph:
    """The supervisor team built once at start-up (Lab 51)."""
    return request.app.state.team_graph


TeamGraph = Annotated[CompiledStateGraph, Depends(get_team_graph)]


def get_network_graph(request: Request) -> CompiledStateGraph:
    """The network of peers built once at start-up (Lab 53)."""
    return request.app.state.network_graph


NetworkGraph = Annotated[CompiledStateGraph, Depends(get_network_graph)]


def team_config() -> dict:
    return {
        "recursion_limit": get_settings().graph_recursion_limit,
        "metadata": {"request_id": get_request_id()},
    }


@router.post("", dependencies=[Depends(model_call_gate)])
async def ask_team(checked: Checked, graph: TeamGraph, context: RunContext) -> TeamResponse:
    """One request, answered by the supervisor and its workers (Lab 51)."""
    result = await graph.ainvoke(
        checked.graph_input, config=team_config(), context=context, output_keys=TEAM_KEYS
    )
    logger.info("Team answered for %s in %d steps", checked.body.client_id, len(result["trail"]))
    return TeamResponse(
        request_id=get_request_id(),
        client_id=checked.body.client_id,
        summary=result["answer"],
        notes=result["notes"],
        trail=result["trail"],
        created_at=datetime.now(UTC),
    )


@router.post(
    "/stream", response_class=EventSourceResponse, dependencies=[Depends(model_call_gate)]
)
async def stream_team(
    checked: Checked, graph: TeamGraph, context: RunContext
) -> AsyncIterator[ServerSentEvent]:
    """The team at work, streamed: every step, including the steps inside sub-teams (Lab 52)."""
    final: dict = {}
    try:
        async for namespace, mode, payload in graph.astream(
            checked.graph_input,
            config=team_config(),
            context=context,
            stream_mode=["updates", "values"],
            subgraphs=True,  # also stream the graphs that run inside the team's nodes
        ):
            if mode == "values":
                if not namespace:  # only the team's own state holds the final answer
                    final = payload
                continue
            path = [part.split(":")[0] for part in namespace]  # "research_desk:<id>" -> name
            for node in payload:
                yield ServerSentEvent(event="node", data={"path": path, "node": node})
    except MODEL_ERRORS as error:
        logger.error("AI model not available during the team stream: %r", error)
        yield ServerSentEvent(event="error", data={"error": "model_unavailable"})
        return
    yield ServerSentEvent(event="answer", data={"summary": final.get("answer", "")})
    yield ServerSentEvent(event="done", data={"client_id": checked.body.client_id})


@router.post(
    "/network", response_class=EventSourceResponse, dependencies=[Depends(model_call_gate)]
)
async def stream_network(
    checked: Checked, graph: NetworkGraph, context: RunContext
) -> AsyncIterator[ServerSentEvent]:
    """Peers handing work to each other, streamed as they negotiate (Lab 53).

    Lab 54: every run is saved as a case under the network's namespace in the shared store.
    """
    case_id = uuid4().hex
    thread = case_thread("network", context.analyst, case_id)
    config = {**team_config(), "configurable": {"thread_id": thread}}
    try:
        async for update in graph.astream(
            checked.graph_input, config=config, context=context, stream_mode="updates"
        ):
            for peer, change in update.items():
                if change and "next" in change:  # a peer finished its part and handed over
                    handoff = {"from": peer, "to": change["next"], "reason": change["task"]}
                    yield ServerSentEvent(event="handoff", data=handoff)
                if change and "answer" in change:
                    yield ServerSentEvent(event="answer", data={"summary": change["answer"]})
    except MODEL_ERRORS as error:
        logger.error("AI model not available during the network stream: %r", error)
        yield ServerSentEvent(event="error", data={"error": "model_unavailable"})
        return
    done = {"client_id": checked.body.client_id, "case_id": case_id}
    yield ServerSentEvent(event="done", data=done)
