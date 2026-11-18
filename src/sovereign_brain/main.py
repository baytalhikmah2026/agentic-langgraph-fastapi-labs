"""The FastAPI application: the reception desk of the Research Desk."""

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from qdrant_client import AsyncQdrantClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker

from sovereign_brain import __version__
from sovereign_brain.api.v1 import (
    agency,
    approvals,
    assistant,
    auth,
    cases,
    clients,
    documents,
    graphs,
    health,
    memory,
    reports,
    research,
    team,
    threads,
    tools,
)
from sovereign_brain.core.cache import ResearchCache
from sovereign_brain.core.errors import register_exception_handlers
from sovereign_brain.core.logging import configure_logging
from sovereign_brain.core.rate_limit import limiter
from sovereign_brain.core.request_id import RequestIdMiddleware
from sovereign_brain.core.settings import get_settings
from sovereign_brain.db.session import create_engine
from sovereign_brain.graphs.report import build_report_graph
from sovereign_brain.graphs.research import build_research_graph
from sovereign_brain.graphs.team.agency import build_agency_graph
from sovereign_brain.graphs.team.briefing import build_briefing_graph
from sovereign_brain.graphs.team.critic import build_critic_graph
from sovereign_brain.graphs.team.mapreduce import build_mapreduce_graph
from sovereign_brain.graphs.team.network import build_network_graph
from sovereign_brain.graphs.team.planner import build_planner_graph
from sovereign_brain.graphs.team.supervisor import build_team_graph
from sovereign_brain.llm.factory import get_chat_model, get_embeddings
from sovereign_brain.memory.checkpoints import open_checkpointer
from sovereign_brain.memory.retention import ThreadRegistry, cleanup_worker
from sovereign_brain.memory.semantic import SemanticMemory
from sovereign_brain.memory.shared_state import open_shared_store
from sovereign_brain.memory.summaries import ThreadArchivist
from sovereign_brain.observability import metrics
from sovereign_brain.observability.tracing import setup_tracing
from sovereign_brain.services.portfolio import PortfolioService
from sovereign_brain.tools.mcp_host import load_mcp_tools

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
    model = get_chat_model(settings)
    # Semantic memory (Lab 38): the Qdrant client connects on first use
    qdrant = AsyncQdrantClient(url=settings.qdrant_url)
    app.state.memory = None
    app.state.archivist = None
    if settings.semantic_memory:
        app.state.memory = SemanticMemory(
            qdrant,
            get_embeddings(settings),
            settings.memory_collection,
            settings.embedding_dimensions,
            settings.memory_min_score,
        )
        logger.info("Semantic memory: Qdrant at %s", settings.qdrant_url)
        # Knowledge nuggets (Lab 40): threads are summarised into memory before they expire
        app.state.archivist = ThreadArchivist(model, app.state.memory)
    # MCP servers (Lab 44): their tools are discovered once and join the tool wall
    app.state.mcp_tools = await load_mcp_tools(settings)
    # The agency's own workspace server (Lab 60): only the developer gets write access
    app.state.agency_tools = await load_mcp_tools(settings, settings.agency_mcp_servers)
    # Thread memory (Lab 32): the checkpointer stays open while the API runs
    async with (
        open_checkpointer(settings) as checkpointer,
        open_shared_store(settings) as shared_store,
    ):
        app.state.research_graph = build_research_graph(
            model, checkpointer=checkpointer, extra_tools=app.state.mcp_tools
        )
        logger.info("Research graph ready (model %s)", settings.llm_model)
        # Reports (Lab 49): a fixed protocol and a strict answer shape
        app.state.report_graph = build_report_graph(model)
        # Approvals (Lab 61): the same protocol, saved, and paused before delivery
        app.state.approval_graph = build_report_graph(
            model, checkpointer=checkpointer, outbox=Path(settings.outbox_dir)
        )
        # The team (Lab 51): a supervisor and its workers, with the same MCP tools
        app.state.team_graph = build_team_graph(model, extra_tools=app.state.mcp_tools)
        # The network (Lab 53): peers that hand work to each other, no editor;
        # every run is saved as a case in the shared store (Lab 54)
        app.state.network_graph = build_network_graph(
            model, extra_tools=app.state.mcp_tools, checkpointer=shared_store
        )
        # A second graph that picks up saved cases through the bridge (Lab 54)
        app.state.briefing_graph = build_briefing_graph(model, checkpointer=shared_store)
        # The writer and its critic (Lab 55): no answer leaves before it passes review
        app.state.critic_graph = build_critic_graph(model)
        # Plan-and-execute (Lab 56): long tasks flown step by step, replanned on failure
        app.state.planner_graph = build_planner_graph(model, extra_tools=app.state.mcp_tools)
        # Map-reduce (Lab 57): many readers at once for one long document
        app.state.mapreduce_graph = build_mapreduce_graph(
            model, chunk_chars=settings.map_chunk_chars, collapse_chars=settings.map_collapse_chars
        )
        # The software agency (Lab 60): PM, developer (workspace MCP) and reviewer (sandbox)
        app.state.agency_graph = build_agency_graph(model, app.state.agency_tools)
        # Thread expiry (Lab 34): a background task that runs as long as the API runs
        worker = asyncio.create_task(
            cleanup_worker(
                app.state.thread_registry,
                app.state.research_graph,
                settings,
                app.state.archivist,
            )
        )
        yield
        worker.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await worker
    await qdrant.close()
    await redis_client.aclose()
    await engine.dispose()
    if app.state.tracer_provider is not None:
        app.state.tracer_provider.shutdown()  # send the last spans before stopping (Lab 66)
    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)
    app.state.limiter = limiter
    register_exception_handlers(app)
    app.add_middleware(RequestIdMiddleware)
    app.state.tracer_provider = setup_tracing(app, settings)  # Lab 66, if switched on
    app.include_router(health.router)
    app.include_router(metrics.router)  # GET /metrics for Prometheus (Lab 68)
    app.include_router(auth.router)
    app.include_router(research.router)
    app.include_router(clients.router)
    app.include_router(graphs.router)
    app.include_router(threads.router)
    app.include_router(memory.router)
    app.include_router(tools.router)
    app.include_router(reports.router)
    app.include_router(assistant.router)
    app.include_router(team.router)
    app.include_router(cases.router)
    app.include_router(documents.router)
    app.include_router(agency.router)
    app.include_router(approvals.router)
    return app


app = create_app()
