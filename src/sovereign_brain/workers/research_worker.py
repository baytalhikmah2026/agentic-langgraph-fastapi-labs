"""The research worker (Lab 83): takes jobs from the queue and runs the research graph.

Start one with:  python -m sovereign_brain.workers.research_worker
In the cluster, KEDA starts workers while jobs wait and stops them when the queue stays empty.
When Kubernetes asks a worker to stop (SIGTERM), it finishes its current job first.
Lab 86: a heartbeat file shows Kubernetes the worker is still alive (see heartbeat.py).
"""

import asyncio
import contextlib
import logging
import signal
import sys

from langgraph.graph.state import CompiledStateGraph
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker

from sovereign_brain.core.logging import configure_logging
from sovereign_brain.core.settings import get_settings
from sovereign_brain.db.session import create_engine
from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.research import build_research_graph
from sovereign_brain.llm.factory import get_chat_model
from sovereign_brain.memory.checkpoints import open_checkpointer
from sovereign_brain.memory.threads import thread_config
from sovereign_brain.services.portfolio import PortfolioService
from sovereign_brain.tools.mcp_host import load_mcp_tools
from sovereign_brain.workers.heartbeat import beat
from sovereign_brain.workers.research_queue import ResearchQueue

logger = logging.getLogger("sovereign_brain.worker")


async def run_job(
    graph: CompiledStateGraph, job_id: str, job: dict, portfolio: PortfolioService
) -> dict:
    """One research run, with the same limits the API uses (semantic memory stays off here)."""
    settings = get_settings()
    context = ResearchContext(
        portfolio=portfolio,
        analyst=job["username"],
        role=job["role"],
        max_revisions=settings.max_revisions,
        router=settings.research_router,
        history_limit=settings.history_limit,
        max_tool_retries=settings.max_tool_retries,
    )
    config = {
        **thread_config(job["thread_key"]),
        "recursion_limit": settings.graph_recursion_limit,
        "metadata": {"job_id": job_id},
    }
    return await graph.ainvoke(job["graph_input"], config=config, context=context)


async def work(stop: asyncio.Event) -> None:
    heart = asyncio.create_task(beat())  # Lab 86: a sign of life for the liveness probe
    settings = get_settings()
    engine = create_engine(settings)
    portfolio = PortfolioService(async_sessionmaker(engine, expire_on_commit=False))
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    queue = ResearchQueue(redis)
    tools = await load_mcp_tools(settings)
    async with open_checkpointer(settings) as checkpointer:
        graph = build_research_graph(
            get_chat_model(settings), checkpointer=checkpointer, extra_tools=tools
        )
        logger.info("Research worker ready, waiting for jobs")
        while not stop.is_set():
            taken = await queue.take(timeout=5)
            if taken is None:
                continue
            job_id, job = taken
            logger.info("Job %s started for %s", job_id, job["graph_input"]["client_id"])
            try:
                result = await run_job(graph, job_id, job, portfolio)
            except Exception as error:  # one failed job must not stop the worker
                logger.exception("Job %s failed", job_id)
                await queue.finish(job_id, error=type(error).__name__)
            else:
                await queue.finish(job_id, result=result)
                logger.info("Job %s completed", job_id)
    logger.info("Research worker stopped")
    heart.cancel()
    await redis.aclose()
    await engine.dispose()


async def run() -> None:
    stop = asyncio.Event()
    with contextlib.suppress(NotImplementedError):  # Windows: stop with Ctrl+C instead
        asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, stop.set)
    await work(stop)


def main() -> None:
    configure_logging(get_settings().log_level)
    # psycopg's async mode needs the "selector" event loop on Windows
    loop_factory = asyncio.SelectorEventLoop if sys.platform == "win32" else None
    asyncio.run(run(), loop_factory=loop_factory)


if __name__ == "__main__":
    main()
