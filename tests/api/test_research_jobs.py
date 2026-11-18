"""Queued research (Lab 83): the API answers at once; a worker finishes the job later."""

import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sovereign_brain.api.v1.research import get_research_queue
from sovereign_brain.workers.research_queue import ResearchQueue

REQUEST = {"client_id": "C-1042", "question": "Summarise the exposure to energy stocks."}


@pytest.fixture
def queue(app: FastAPI, fake_redis) -> ResearchQueue:
    queue = ResearchQueue(fake_redis)
    app.dependency_overrides[get_research_queue] = lambda: queue
    return queue


def test_a_queued_job_belongs_to_its_analyst(
    client: TestClient,
    auth_headers: dict[str, str],
    omar_headers: dict[str, str],
    queue: ResearchQueue,
) -> None:
    queued = client.post("/v1/research/jobs", json=REQUEST, headers=auth_headers)
    job_id = queued.json()["job_id"]
    mine = client.get(f"/v1/research/jobs/{job_id}", headers=auth_headers)
    theirs = client.get(f"/v1/research/jobs/{job_id}", headers=omar_headers)

    assert queued.status_code == 202
    assert mine.json()["status"] == "queued"
    assert mine.json()["summary"] is None
    assert theirs.status_code == 404


def test_the_answer_appears_once_a_worker_finishes(
    client: TestClient, auth_headers: dict[str, str], queue: ResearchQueue
) -> None:
    job_id = client.post("/v1/research/jobs", json=REQUEST, headers=auth_headers).json()["job_id"]
    result = {"answer": "Energy is 18.5% of the portfolio.", "route": "portfolio", "checked": True}

    taken_id, job = asyncio.run(queue.take())  # what a worker does first
    asyncio.run(queue.finish(taken_id, result=result))  # ... and last
    body = client.get(f"/v1/research/jobs/{job_id}", headers=auth_headers).json()

    assert taken_id == job_id
    assert job["graph_input"]["client_id"] == "C-1042"
    assert body["status"] == "completed"
    assert body["summary"] == "Energy is 18.5% of the portfolio."
    assert body["route"] == "portfolio"
