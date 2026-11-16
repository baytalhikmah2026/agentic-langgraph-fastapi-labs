"""Memory housekeeping: retention report and clean-up on request (Lab 34)."""

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from sovereign_brain.api.v1.research import Registry, ResearchGraph
from sovereign_brain.core.security import get_current_user
from sovereign_brain.core.settings import get_settings
from sovereign_brain.memory.retention import collect_garbage
from sovereign_brain.schemas.memory import CleanupResult, RetentionReport

router = APIRouter(prefix="/v1/memory", tags=["memory"], dependencies=[Depends(get_current_user)])


@router.get("/retention")
async def retention_report(registry: Registry) -> RetentionReport:
    """The compliance view: threads kept, threads overdue, and what was cleared so far."""
    ttl = get_settings().thread_ttl_minutes
    numbers = await registry.report(datetime.now(UTC) - timedelta(minutes=ttl))
    return RetentionReport(ttl_minutes=ttl, **numbers)


@router.post("/cleanup")
async def cleanup_now(
    registry: Registry,
    graph: ResearchGraph,
    older_than_minutes: Annotated[int | None, Query(ge=0)] = None,
) -> CleanupResult:
    """Run the clean-up now; `older_than_minutes` overrides the TTL for this run only."""
    minutes = older_than_minutes
    if minutes is None:
        minutes = get_settings().thread_ttl_minutes
    removed = await collect_garbage(
        registry, graph.checkpointer, timedelta(minutes=minutes), "manual"
    )
    return CleanupResult(removed=removed)
