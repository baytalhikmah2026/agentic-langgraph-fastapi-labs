"""Team cases (Labs 54-55): work saved by one graph, picked up, briefed and reviewed by others."""

import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from fastapi.sse import EventSourceResponse, ServerSentEvent
from langgraph.graph.state import CompiledStateGraph
from pydantic import ValidationError

from sovereign_brain.api.v1.research import RunContext
from sovereign_brain.api.v1.team import NetworkGraph
from sovereign_brain.core.errors import MODEL_ERRORS
from sovereign_brain.core.rate_limit import model_call_gate
from sovereign_brain.core.security import CurrentUser, get_current_user
from sovereign_brain.graphs.team.bridge import CaseFile, CaseNotFound, export_case
from sovereign_brain.memory.shared_state import case_thread
from sovereign_brain.schemas.team import BriefingResponse

router = APIRouter(prefix="/v1/cases", tags=["cases"], dependencies=[Depends(get_current_user)])
logger = logging.getLogger("sovereign_brain.team")
CaseId = Annotated[str, Path(pattern=r"^[0-9a-f]{32}$")]


def get_briefing_graph(request: Request) -> CompiledStateGraph:
    """The briefing graph built once at start-up (Lab 54)."""
    return request.app.state.briefing_graph


BriefingGraph = Annotated[CompiledStateGraph, Depends(get_briefing_graph)]


def get_critic_graph(request: Request) -> CompiledStateGraph:
    """The writer-and-critic graph built once at start-up (Lab 55)."""
    return request.app.state.critic_graph


CriticGraph = Annotated[CompiledStateGraph, Depends(get_critic_graph)]


async def checked_case(case_id: CaseId, network: NetworkGraph, user: CurrentUser) -> CaseFile:
    """The case as it crosses the bridge: found, owned by this analyst, and complete."""
    try:
        return await export_case(network, user.username, case_id)
    except CaseNotFound:
        raise HTTPException(status_code=404, detail="Case not found") from None
    except ValidationError as error:
        fields = sorted({str(e["loc"][0]) for e in error.errors()})
        logger.warning("Case %s turned back at the bridge: %s", case_id, fields)
        raise HTTPException(status_code=409, detail=f"Case incomplete: {fields}") from None


Case = Annotated[CaseFile, Depends(checked_case)]


@router.get("/{case_id}")
async def get_case(case: Case) -> CaseFile:
    """A saved team case, exactly as other graphs receive it."""
    return case


@router.post("/{case_id}/briefing", dependencies=[Depends(model_call_gate)])
async def write_briefing(case: Case, graph: BriefingGraph, user: CurrentUser) -> BriefingResponse:
    """A second graph picks up the case and writes the relationship manager's briefing."""
    thread = case_thread("briefing", user.username, case.case_id)
    result = await graph.ainvoke(
        {"case": case.model_dump()}, config={"configurable": {"thread_id": thread}}
    )
    return BriefingResponse(
        case_id=case.case_id,
        client_id=case.client_id,
        briefing=result["briefing"],
        created_at=datetime.now(UTC),
    )


@router.post(
    "/{case_id}/review", response_class=EventSourceResponse, dependencies=[Depends(model_call_gate)]
)
async def review_case(
    case: Case, graph: CriticGraph, context: RunContext
) -> AsyncIterator[ServerSentEvent]:
    """The final answer, drafted and criticised until it is right, streamed round by round."""
    final = {"draft": "", "verdict": "", "rounds": 0}
    try:
        async for update in graph.astream(
            {"case": case.model_dump()}, context=context, stream_mode="updates"
        ):
            for change in update.values():
                for entry in change.get("history", []):  # the internal monologue, as it happens
                    yield ServerSentEvent(event=entry["step"], data=entry)
                final.update({k: v for k, v in change.items() if k in final})
    except MODEL_ERRORS as error:
        logger.error("AI model not available during the case review: %r", error)
        yield ServerSentEvent(event="error", data={"error": "model_unavailable"})
        return
    yield ServerSentEvent(event="final", data={"case_id": case.case_id, **final})
