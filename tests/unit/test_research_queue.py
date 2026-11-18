"""The research queue (Lab 83): jobs come out oldest first, with their status and result."""

from sovereign_brain.workers.research_queue import WORKING, ResearchQueue, job_key

FIRST, SECOND = "a" * 32, "b" * 32


async def test_jobs_come_out_oldest_first(fake_redis) -> None:
    queue = ResearchQueue(fake_redis)
    await queue.enqueue(FIRST, {"question": 1})
    await queue.enqueue(SECOND, {"question": 2})

    taken = await queue.take()

    assert taken == (FIRST, {"question": 1})
    assert await queue.waiting() == 1
    assert fake_redis.lists[WORKING] == [FIRST]
    assert (await queue.status(FIRST))["status"] == "running"


async def test_a_finished_job_keeps_its_result(fake_redis) -> None:
    queue = ResearchQueue(fake_redis)
    await queue.enqueue(FIRST, {"question": 1})
    await queue.take()

    await queue.finish(FIRST, result={"answer": "Done."})

    status = await queue.status(FIRST)
    assert status["status"] == "completed"
    assert status["result"] == {"answer": "Done."}
    assert fake_redis.lists[WORKING] == []


async def test_an_expired_job_is_skipped(fake_redis) -> None:
    queue = ResearchQueue(fake_redis)
    await queue.enqueue(FIRST, {"question": 1})
    del fake_redis.hashes[job_key(FIRST)]  # as if its hour had passed while it waited

    assert await queue.take() is None
    assert fake_redis.lists[WORKING] == []
