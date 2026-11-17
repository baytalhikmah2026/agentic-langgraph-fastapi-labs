"""The Infinite-Memory agent over the API (Lab 40): archive, clean-up with summaries, and
memories that stay with their analyst."""

from collections.abc import Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from sovereign_brain.api.v1.research import get_archivist, get_memory
from sovereign_brain.memory.semantic import SemanticMemory
from sovereign_brain.memory.summaries import ThreadArchivist

SUMMARY = "The analyst asked about the energy exposure; the desk called it modest."
REQUEST = {
    "client_id": "C-1042",
    "question": "Summarise the energy exposure.",
    "thread_id": "energy-review",
}
RECALL = {"client_id": "C-1042", "question": "energy exposure"}


@pytest.fixture
def memory(
    app: FastAPI, make_memory: Callable[[], SemanticMemory], make_model: Callable
) -> SemanticMemory:
    """Switches semantic memory on, with an archivist whose model writes SUMMARY."""
    memory = make_memory()
    archivist = ThreadArchivist(make_model([AIMessage(SUMMARY)]), memory)
    app.dependency_overrides[get_memory] = lambda: memory
    app.dependency_overrides[get_archivist] = lambda: archivist
    return memory


def test_a_thread_is_archived_into_memory(
    client: TestClient, auth_headers: dict[str, str], memory: SemanticMemory
) -> None:
    client.post("/v1/research", json=REQUEST, headers=auth_headers)

    response = client.post("/v1/threads/energy-review/archive", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {"thread_id": "energy-review", "summary": SUMMARY}
    assert client.get("/v1/threads/energy-review", headers=auth_headers).status_code == 404
    found = client.get("/v1/memory/recall", params=RECALL, headers=auth_headers).json()
    assert SUMMARY in [item["answer"] for item in found]


def test_the_cleanup_keeps_a_summary_of_each_thread(
    client: TestClient, auth_headers: dict[str, str], memory: SemanticMemory
) -> None:
    client.post("/v1/research", json=REQUEST, headers=auth_headers)

    cleanup = client.post("/v1/memory/cleanup?older_than_minutes=0", headers=auth_headers)

    assert cleanup.json() == {"removed": 1, "summarised": 1}


def test_memories_stay_with_their_analyst(
    client: TestClient,
    auth_headers: dict[str, str],
    omar_headers: dict[str, str],
    memory: SemanticMemory,
) -> None:
    client.post("/v1/research", json=REQUEST, headers=auth_headers)

    amina = client.get("/v1/memory/recall", params=RECALL, headers=auth_headers).json()
    omar = client.get("/v1/memory/recall", params=RECALL, headers=omar_headers).json()

    assert len(amina) == 1
    assert omar == []


def test_archiving_needs_semantic_memory(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    client.post("/v1/research", json=REQUEST, headers=auth_headers)

    response = client.post("/v1/threads/energy-review/archive", headers=auth_headers)

    assert response.status_code == 503
