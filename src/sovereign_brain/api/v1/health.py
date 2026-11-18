"""Health checks: is the application alive, and is it ready to serve (Lab 86)?"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import text

from sovereign_brain import __version__
from sovereign_brain.core.settings import get_settings

router = APIRouter(tags=["health"])
Check = Callable[[], Awaitable[object]]
CHECK_TIMEOUT_SECONDS = 2


@router.get("/health")
async def health() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "app": settings.app_name, "version": __version__}


@router.get("/health/live")
async def live() -> dict[str, str]:
    """Liveness: the process answers. Nothing else is checked, on purpose."""
    return {"status": "alive"}


def readiness_checks(request: Request) -> dict[str, Check]:
    """What this pod needs to serve requests: its database and its Redis."""
    state = request.app.state

    async def database() -> None:
        async with state.session_factory() as session:
            await session.execute(text("SELECT 1"))

    return {"database": database, "redis": state.research_queue.redis.ping}


@router.get("/health/ready")
async def ready(
    response: Response, checks: Annotated[dict[str, Check], Depends(readiness_checks)]
) -> dict[str, object]:
    """Readiness: every check answers within 2 seconds, or this pod gets no traffic (503)."""
    results: dict[str, str] = {}
    for name, check in checks.items():
        try:
            await asyncio.wait_for(check(), timeout=CHECK_TIMEOUT_SECONDS)
            results[name] = "ok"
        except Exception as error:  # any failure means "not ready", never a crash
            results[name] = type(error).__name__
    is_ready = all(result == "ok" for result in results.values())
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ready" if is_ready else "not_ready", "checks": results}
