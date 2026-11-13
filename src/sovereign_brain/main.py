"""The FastAPI application: the reception desk of the Research Desk."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker

from sovereign_brain import __version__
from sovereign_brain.api.v1 import clients, health, research
from sovereign_brain.core.errors import register_exception_handlers
from sovereign_brain.core.logging import configure_logging
from sovereign_brain.core.settings import get_settings
from sovereign_brain.db.session import create_engine
from sovereign_brain.graphs.hello import build_hello_graph
from sovereign_brain.llm.factory import get_chat_model

logger = logging.getLogger("sovereign_brain")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logger.info("Starting %s %s (%s)", settings.app_name, __version__, settings.environment)
    engine = create_engine(settings)
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)
    app.state.research_graph = build_hello_graph(get_chat_model(settings))
    logger.info("Research graph ready (model %s)", settings.llm_model)
    yield
    await engine.dispose()
    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)
    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(research.router)
    app.include_router(clients.router)
    return app


app = create_app()
