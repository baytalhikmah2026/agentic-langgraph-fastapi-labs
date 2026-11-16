"""Resuming over the API (Lab 35): POST /v1/threads/{thread_id}/resume."""

import itertools
from collections.abc import Callable

from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

from sovereign_brain.api.v1.research import get_research_graph
from sovereign_brain.graphs.research import build_research_graph

REQUEST = {"client_id": "C-1042", "question": "What is a bond?", "thread_id": "bond-basics"}


def test_an_interrupted_run_can_be_resumed(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    make_flaky_model: Callable,
    fake_answer: str,
) -> None:
    # Call 1 is the model router, call 2 the explain station: the model is down for call 2
    model = make_flaky_model(itertools.repeat(AIMessage(fake_answer)), fail_on_call=2)
    graph = build_research_graph(model, checkpointer=InMemorySaver())
    app.dependency_overrides[get_research_graph] = lambda: graph

    failed = client.post("/v1/research", json=REQUEST, headers=auth_headers)
    thread = client.get("/v1/threads/bond-basics", headers=auth_headers).json()
    resumed = client.post("/v1/threads/bond-basics/resume", headers=auth_headers)

    assert failed.status_code == 503
    assert thread["next"] == ["explain"]
    assert resumed.status_code == 200
    assert resumed.json()["summary"] == fake_answer
    assert resumed.json()["thread_id"] == "bond-basics"
    after = client.get("/v1/threads/bond-basics", headers=auth_headers).json()
    assert after["next"] == []
    assert after["turns"] == 1  # the question was asked once: nothing was repeated


def test_a_finished_thread_has_nothing_to_resume(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    client.post("/v1/research", json=REQUEST, headers=auth_headers)

    response = client.post("/v1/threads/bond-basics/resume", headers=auth_headers)

    assert response.status_code == 409
    assert response.json()["error"] == "conflict"
    assert response.json()["message"] == "Thread bond-basics has no interrupted run to resume"
