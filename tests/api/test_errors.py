import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langgraph.errors import GraphRecursionError

from sovereign_brain.api.v1.research import get_research_graph

REQUEST = {"client_id": "C-1042", "question": "Summarise the exposure to energy stocks."}


class FailingGraph:
    """Stands in for the graph and raises the given error."""

    def __init__(self, error: Exception) -> None:
        self.error = error

    async def ainvoke(self, *args, **kwargs):
        raise self.error


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (ConnectionError("Failed to connect to Ollama"), 503, "model_unavailable"),
        (httpx.ConnectError("connection refused"), 503, "model_unavailable"),
        (GraphRecursionError("Recursion limit of 25 reached"), 508, "agent_loop_limit"),
        (RuntimeError("secret internal detail"), 500, "internal_error"),
    ],
)
def test_failures_become_clear_error_answers(
    app: FastAPI, password: str, error: Exception, status: int, code: str
) -> None:
    app.dependency_overrides[get_research_graph] = lambda: FailingGraph(error)
    with TestClient(app, raise_server_exceptions=False) as client:
        login = client.post("/v1/auth/token", data={"username": "amina", "password": password})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        response = client.post("/v1/research", json=REQUEST, headers=headers)

    assert response.status_code == status
    assert response.json()["error"] == code
    assert "secret" not in response.text
