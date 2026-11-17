"""One shared store for several graphs (Lab 54): Redis, with one namespace per graph.

SB_SHARED_STATE_STORE chooses it:
- "memory": in the API process; lost on every restart; used by the tests.
- "redis": the project's Redis (Redis 8 includes the JSON and search features the Redis
  checkpointer needs). Every saved case expires after SB_CASE_TTL_MINUTES.
Each graph writes under its own namespace in the thread ID, so two graphs can save the same
case without ever overwriting each other.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.redis.aio import AsyncRedisSaver

from sovereign_brain.core.settings import Settings

logger = logging.getLogger("sovereign_brain.memory")


def case_thread(graph: str, owner: str, case_id: str) -> str:
    """Namespace partitioning: "<graph>:<owner>:<case>", so graphs and analysts never collide."""
    return f"{graph}:{owner}:{case_id}"


@asynccontextmanager
async def open_shared_store(settings: Settings) -> AsyncIterator[BaseCheckpointSaver]:
    """Open the shared store for the lifetime of the API, and close it afterwards."""
    if settings.shared_state_store == "redis":
        ttl = {"default_ttl": settings.case_ttl_minutes, "refresh_on_read": True}
        async with AsyncRedisSaver.from_conn_string(settings.redis_url, ttl=ttl) as saver:
            logger.info("Shared state: Redis, cases kept %d minutes", settings.case_ttl_minutes)
            yield saver
        return
    logger.info("Shared state: in memory (lost on restart)")
    yield InMemorySaver()
