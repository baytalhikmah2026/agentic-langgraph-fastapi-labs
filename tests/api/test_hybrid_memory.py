"""Hybrid memory over the API (Lab 39): the trail shows recall before and remember after."""

from collections.abc import Callable

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sovereign_brain.api.v1.research import get_memory
from sovereign_brain.memory.semantic import SemanticMemory


def test_a_new_thread_recalls_an_earlier_answer(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    make_memory: Callable[[], SemanticMemory],
) -> None:
    memory = make_memory()
    app.dependency_overrides[get_memory] = lambda: memory
    first = {
        "client_id": "C-1042",
        "question": "Summarise the energy exposure.",
        "thread_id": "energy-review",
    }
    second = {
        "client_id": "C-1042",
        "question": "Is the energy exposure a risk?",
        "thread_id": "energy-risk",
    }
    client.post("/v1/research", json=first, headers=auth_headers)

    body = client.post("/v1/research/trace", json=second, headers=auth_headers).json()

    stations = [step["node"] for step in body["trail"]]
    assert stations == ["intake", "recall", "classify", "analyse", "review", "remember"]
    assert body["trail"][1]["note"] == "Related answers from earlier conversations: 1"
