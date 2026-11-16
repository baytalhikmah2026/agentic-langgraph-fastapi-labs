"""What the API reports about memory retention (Lab 34)."""

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
