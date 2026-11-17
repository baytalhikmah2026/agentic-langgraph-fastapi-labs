"""The FastAPI application: the reception desk of the Research Desk."""

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from qdrant_client import AsyncQdrantClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker

from sovereign_brain import __version__
from sovereign_brain.api.v1 import auth, clients, graphs, health, memory, research, threads
from sovereign_brain.core.cache import ResearchCache
from sovereign_brain.core.errors import register_exception_handlers
from sovereign_brain.core.logging import configure_logging
from sovereign_brain.core.rate_limit import limiter
from sovereign_brain.core.request_id import RequestIdMiddleware
from sovereign_brain.core.settings import get_settings
from sovereign_brain.db.session import create_engine
from sovereign_brain.graphs.research import build_research_graph
from sovereign_brain.llm.factory import get_chat_model, get_embeddings
from sovereign_brain.memory.checkpoints import open_checkpointer
from sovereign_brain.memory.retention import ThreadRegistry, cleanup_worker
from sovereign_brain.memory.semantic import SemanticMemory
from sovereign_brain.services.portfolio import PortfolioService

logger = logging.getLogger("sovereign_brain")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logger.info("Starting %s %s (%s)", settings.app_name, __version__, settings.environment)
    engine = create_engine(settings)
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)
    redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    app.state.cache = ResearchCache(redis_client, settings.cache_ttl_seconds)
    # Services live on app.state and reach each run through its context (Lab 28)
    app.state.portfolio = PortfolioService(app.state.session_factory)
    app.state.thread_registry = ThreadRegistry(app.state.session_factory)
    # Semantic memory (Lab 38): the Qdrant client connects on first use
    qdrant = AsyncQdrantClient(url=settings.qdrant_url)
    app.state.memory = None
    if settings.semantic_memory:
        app.state.memory = SemanticMemory(
            qdrant,
            get_embeddings(settings),
            settings.memory_collection,
            settings.embedding_dimensions,
            settings.memory_min_score,
        )
        logger.info("Semantic memory: Qdrant at %s", settings.qdrant_url)
    # Thread memory (Lab 32): the checkpointer stays open while the API runs
    async with open_checkpointer(settings) as checkpointer:
        app.state.research_graph = build_research_graph(
            get_chat_model(settings), checkpointer=checkpointer
        )
        logger.info("Research graph ready (model %s)", settings.llm_model)
        # Thread expiry (Lab 34): a background task that runs as long as the API runs
        worker = asyncio.create_task(
            cleanup_worker(app.state.thread_registry, checkpointer, settings)
        )
        yield
        worker.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await worker
    await qdrant.close()
    await redis_client.aclose()
    await engine.dispose()
    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)
    app.state.limiter = limiter
    register_exception_handlers(app)
    app.add_middleware(RequestIdMiddleware)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(research.router)
    app.include_router(clients.router)
    app.include_router(graphs.router)
    app.include_router(threads.router)
    app.include_router(memory.router)
    return app


app = create_app()
