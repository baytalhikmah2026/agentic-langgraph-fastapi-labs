"""Recalling remembered answers over the API (Lab 38)."""

from collections.abc import Callable

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sovereign_brain.api.v1.research import get_memory
from sovereign_brain.memory.semantic import SemanticMemory

RECALL = {"client_id": "C-1042", "question": "energy exposure"}


def test_answers_can_be_recalled_by_meaning(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    make_memory: Callable[[], SemanticMemory],
    fake_answer: str,
) -> None:
    memory = make_memory()
    app.dependency_overrides[get_memory] = lambda: memory
    question = {"client_id": "C-1042", "question": "Summarise the energy exposure."}
    client.post("/v1/research", json=question, headers=auth_headers)

    response = client.get("/v1/memory/recall", params=RECALL, headers=auth_headers)

    assert response.status_code == 200
    [found] = response.json()
    assert found["answer"] == fake_answer
    assert found["owner"] == "amina"
    assert found["route"] == "portfolio"


def test_recall_needs_semantic_memory(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/v1/memory/recall", params=RECALL, headers=auth_headers)

    assert response.status_code == 503
    assert response.json()["error"] == "service_unavailable"
