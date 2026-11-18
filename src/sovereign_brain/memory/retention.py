"""Thread expiry and clean-up (Lab 34): conversations are kept only as long as needed.

Every research run marks its thread as used. Threads unused for longer than
SB_THREAD_TTL_MINUTES are removed (checkpoints and record) by a worker that runs every
SB_CLEANUP_INTERVAL_MINUTES, or on request. Each clean-up is recorded as evidence.
Lab 40: with semantic memory on, each thread is summarised into Qdrant before it is erased.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from langgraph.graph.state import CompiledStateGraph
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sovereign_brain.core.settings import Settings
from sovereign_brain.db.models import ResearchThread, ThreadCleanup
from sovereign_brain.memory.summaries import ThreadArchivist

logger = logging.getLogger("sovereign_brain.memory")


class ThreadRegistry:
    """Which threads exist, whose they are, and when each was last used."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self.sessions = sessions

    async def touch(self, key: str, owner: str, thread_id: str, client_id: str) -> None:
        """Record that a thread was just used (and register it the first time)."""
        now = datetime.now(UTC)
        async with self.sessions() as session:
            thread = await session.get(ResearchThread, key)
            if thread is None:
                session.add(
                    ResearchThread(
                        key=key,
                        owner=owner,
                        thread_id=thread_id,
                        client_id=client_id,
                        created_at=now,
                        last_used_at=now,
                    )
                )
            else:
                thread.last_used_at = now
            await session.commit()

    async def forget(self, key: str) -> None:
        async with self.sessions() as session:
            thread = await session.get(ResearchThread, key)
            if thread is not None:
                await session.delete(thread)
                await session.commit()

    async def keys_for_client(self, client_id: str) -> list[str]:
        """Keys of every thread about one client, for every analyst (Lab 78: erasure)."""
        query = select(ResearchThread.key).where(ResearchThread.client_id == client_id)
        async with self.sessions() as session:
            return list((await session.scalars(query)).all())

    async def unused_since(self, cutoff: datetime) -> list[str]:
        """Keys of the threads not used since the cutoff time."""
        query = select(ResearchThread.key).where(ResearchThread.last_used_at < cutoff)
        async with self.sessions() as session:
            return list((await session.scalars(query)).all())

    async def record_cleanup(self, removed: int, trigger: str) -> None:
        async with self.sessions() as session:
            session.add(
                ThreadCleanup(ran_at=datetime.now(UTC), threads_removed=removed, trigger=trigger)
            )
            await session.commit()

    async def report(self, cutoff: datetime) -> dict:
        """The numbers for the retention report."""
        async with self.sessions() as session:
            active = await session.scalar(select(func.count()).select_from(ResearchThread))
            waiting = await session.scalar(
                select(func.count()).where(ResearchThread.last_used_at < cutoff)
            )
            runs, removed, last = (
                await session.execute(
                    select(
                        func.count(ThreadCleanup.id),
                        func.coalesce(func.sum(ThreadCleanup.threads_removed), 0),
                        func.max(ThreadCleanup.ran_at),
                    )
                )
            ).one()
        return {
            "active_threads": active,
            "expired_waiting": waiting,
            "cleanups": runs,
            "threads_removed": removed,
            "last_cleanup_at": last,
        }


async def collect_garbage(
    registry: ThreadRegistry,
    graph: CompiledStateGraph,
    older_than: timedelta,
    trigger: str,
    archivist: ThreadArchivist | None = None,
) -> tuple[int, int]:
    """Remove every thread unused for longer than `older_than`; returns (removed, summarised).

    With an archivist (Lab 40), each thread is summarised into semantic memory first.
    """
    keys = await registry.unused_since(datetime.now(UTC) - older_than)
    summarised = 0
    for key in keys:
        if archivist is not None:
            try:
                if await archivist.archive(graph, key) is not None:
                    summarised += 1
            except Exception as error:  # the retention promise comes first: erase anyway
                logger.warning("Thread %s not summarised: %r", key, error)
        await graph.checkpointer.adelete_thread(key)
        await registry.forget(key)
    await registry.record_cleanup(len(keys), trigger)
    logger.info("Thread clean-up (%s): %d removed, %d summarised", trigger, len(keys), summarised)
    return len(keys), summarised


async def cleanup_worker(
    registry: ThreadRegistry,
    graph: CompiledStateGraph,
    settings: Settings,
    archivist: ThreadArchivist | None = None,
) -> None:
    """Runs for as long as the API runs: wait, clean up, repeat."""
    while True:
        await asyncio.sleep(settings.cleanup_interval_minutes * 60)
        try:
            ttl = timedelta(minutes=settings.thread_ttl_minutes)
            await collect_garbage(registry, graph, ttl, "worker", archivist)
        except Exception:  # one failed round must not stop the worker
            logger.exception("Thread clean-up failed; trying again next round")
