"""The Project Command Center (Lab 60): one call runs a whole development cycle."""

import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from langgraph.graph.state import CompiledStateGraph

from sovereign_brain.api.v1.research import RunContext
from sovereign_brain.core.rate_limit import model_call_gate
from sovereign_brain.core.request_id import get_request_id
from sovereign_brain.core.security import get_current_user
from sovereign_brain.core.settings import get_settings
from sovereign_brain.schemas.agency import AgencyRequest, AgencyResponse

router = APIRouter(prefix="/v1/agency", tags=["agency"], dependencies=[Depends(get_current_user)])
logger = logging.getLogger("sovereign_brain.agency")


def get_agency_graph(request: Request) -> CompiledStateGraph:
    """The PM, developer and reviewer, built once at start-up (Lab 60)."""
    return request.app.state.agency_graph


AgencyGraph = Annotated[CompiledStateGraph, Depends(get_agency_graph)]


@router.post("", dependencies=[Depends(model_call_gate)])
async def run_cycle(
    body: AgencyRequest, graph: AgencyGraph, context: RunContext
) -> AgencyResponse:
    """Spec, code, test, fix: until the check passes or the rounds run out."""
    config = {
        "recursion_limit": get_settings().graph_recursion_limit,
        "metadata": {"request_id": get_request_id()},
    }
    result = await graph.ainvoke({"request": body.request}, config=config, context=context)
    filename = result.get("spec", {}).get("filename")
    verdict, rounds = result["verdict"], result["rounds"]
    logger.info("Agency cycle for %s: %s after %d round(s)", filename, verdict, rounds)
    return AgencyResponse(
        request_id=get_request_id(),
        filename=filename,
        verdict=verdict,
        rounds=rounds,
        test_output=result.get("test_output", ""),
        trail=result["trail"],
        created_at=datetime.now(UTC),
    )
