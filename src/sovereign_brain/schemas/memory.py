"""What the API reports about memory retention (Lab 34) and archiving (Lab 40)."""

from datetime import datetime

from pydantic import BaseModel


class RetentionReport(BaseModel):
    """How long threads are kept, how many exist, and what the clean-ups removed."""

    ttl_minutes: int
    active_threads: int
    expired_waiting: int  # unused for longer than the TTL, removed at the next clean-up
    cleanups: int
    threads_removed: int
    last_cleanup_at: datetime | None = None


class CleanupResult(BaseModel):
    removed: int
    summarised: int = 0  # threads kept as knowledge nuggets in semantic memory (Lab 40)


class ArchiveResult(BaseModel):
    """A thread summarised into semantic memory and then erased (Lab 40)."""

    thread_id: str
    summary: str
