"""The Research Desk team (Module 6): requests answered by several agents together."""

import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from langgraph.graph.state import CompiledStateGraph

from sovereign_brain.api.v1.research import Checked, RunContext
from sovereign_brain.core.rate_limit import model_call_gate
from sovereign_brain.core.request_id import get_request_id
from sovereign_brain.core.security import get_current_user
from sovereign_brain.core.settings import get_settings
from sovereign_brain.schemas.team import TeamResponse

router = APIRouter(prefix="/v1/team", tags=["team"], dependencies=[Depends(get_current_user)])
logger = logging.getLogger("sovereign_brain.team")
# The output fields plus the trail: who did what, in order
TEAM_KEYS = ["answer", "notes", "trail"]


def get_team_graph(request: Request) -> CompiledStateGraph:
    """The supervisor team built once at start-up (Lab 51)."""
    return request.app.state.team_graph


TeamGraph = Annotated[CompiledStateGraph, Depends(get_team_graph)]


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
