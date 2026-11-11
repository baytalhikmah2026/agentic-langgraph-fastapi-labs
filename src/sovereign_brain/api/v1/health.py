"""Health check: answers as long as the application is alive."""

from fastapi import APIRouter

from sovereign_brain import __version__
from sovereign_brain.core.settings import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "app": settings.app_name, "version": __version__}
