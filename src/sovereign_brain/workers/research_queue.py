"""The research queue (Lab 83): research jobs wait in Redis, and workers take them in order.

The API checks a request (badge, injection guard, client, masking), saves it as a job and
answers at once. A worker takes the oldest job, runs the research graph and writes the result
back. KEDA counts the jobs waiting in QUEUE and starts workers only when there is work.
"""

import json
from datetime import UTC, datetime

from redis.asyncio import Redis

QUEUE = "research:queue"  # job IDs waiting for a worker (KEDA watches this list)
WORKING = "research:working"  # job IDs a worker has taken and not finished yet
JOB_TTL_SECONDS = 3600  # a job and its result are kept for one hour


def job_key(job_id: str) -> str:
    return f"research:job:{job_id}"


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class ResearchQueue:
    """Puts jobs on the queue, hands them to workers, and keeps their status and result."""

    def __init__(self, redis: Redis) -> None:
        self.redis = redis  # created with decode_responses=True: answers are text

    async def enqueue(self, job_id: str, job: dict) -> None:
        """Save the job record first, then put its ID at the back of the queue."""
        record = {"job": json.dumps(job), "status": "queued", "queued_at": now()}
        await self.redis.hset(job_key(job_id), mapping=record)
        await self.redis.expire(job_key(job_id), JOB_TTL_SECONDS)
        await self.redis.lpush(QUEUE, job_id)

    async def take(self, timeout: int = 5) -> tuple[str, dict] | None:
        """The oldest waiting job, moved to the working list; None when nothing comes in time."""
        job_id = await self.redis.blmove(QUEUE, WORKING, timeout, "RIGHT", "LEFT")
        if job_id is None:
            return None
        raw = await self.redis.hget(job_key(job_id), "job")
        if raw is None:  # the record expired while the job was waiting
            await self.redis.lrem(WORKING, 1, job_id)
            return None
        await self.redis.hset(job_key(job_id), mapping={"status": "running", "started_at": now()})
        return job_id, json.loads(raw)

    async def finish(self, job_id: str, result: dict | None = None, error: str = "") -> None:
        """Write the result (or the error) and take the job off the working list."""
        fields = {"status": "failed" if error else "completed", "finished_at": now()}
        if result is not None:
            fields["result"] = json.dumps(result)
        if error:
            fields["error"] = error
        await self.redis.hset(job_key(job_id), mapping=fields)
        await self.redis.lrem(WORKING, 1, job_id)

    async def status(self, job_id: str) -> dict | None:
        """The job's record with its status and result, or None when it doesn't exist."""
        record = await self.redis.hgetall(job_key(job_id))
        if not record:
            return None
        return {
            "status": record["status"],
            "job": json.loads(record["job"]),
            "result": json.loads(record["result"]) if "result" in record else None,
            "error": record.get("error"),
        }

    async def waiting(self) -> int:
        """How many jobs wait for a worker right now."""
        return await self.redis.llen(QUEUE)
