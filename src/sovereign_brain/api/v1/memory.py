"""Memory housekeeping (Labs 34, 40) and semantic recall (Lab 38)."""

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from sovereign_brain.api.v1.research import Archivist, Memory, Registry, ResearchGraph
from sovereign_brain.core.security import CurrentUser, get_current_user
from sovereign_brain.core.settings import get_settings
from sovereign_brain.memory.retention import collect_garbage
from sovereign_brain.memory.semantic import Recollection
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
    archivist: Archivist,
    older_than_minutes: Annotated[int | None, Query(ge=0)] = None,
) -> CleanupResult:
    """Run the clean-up now; `older_than_minutes` overrides the TTL for this run only."""
    minutes = older_than_minutes
    if minutes is None:
        minutes = get_settings().thread_ttl_minutes
    removed, summarised = await collect_garbage(
        registry, graph, timedelta(minutes=minutes), "manual", archivist
    )
    return CleanupResult(removed=removed, summarised=summarised)


@router.get("/recall")
async def recall(
    user: CurrentUser,
    memory: Memory,
    client_id: Annotated[str, Query(pattern=r"^C-\d{4}$")],
    question: Annotated[str, Query(min_length=3, max_length=500)],
    limit: Annotated[int, Query(ge=1, le=10)] = 3,
) -> list[Recollection]:
    """Your remembered answers for one client, closest in meaning to `question` (Lab 38)."""
    if memory is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Semantic memory is switched off")
    return await memory.recall(user.username, client_id, question, limit)
