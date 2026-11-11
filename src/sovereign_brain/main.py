"""The FastAPI application: the reception desk of the Research Desk."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from sovereign_brain import __version__
from sovereign_brain.api.v1 import health
from sovereign_brain.core.logging import configure_logging
from sovereign_brain.core.settings import get_settings

logger = logging.getLogger("sovereign_brain")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logger.info("Starting %s %s (%s)", settings.app_name, __version__, settings.environment)
    yield
    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)
    app.include_router(health.router)
    return app


app = create_app()
