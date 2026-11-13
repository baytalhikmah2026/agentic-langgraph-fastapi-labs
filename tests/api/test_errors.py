import httpx
from fastapi.testclient import TestClient
from langgraph.errors import GraphRecursionError

from sovereign_brain.api.v1.research import get_research_graph
from sovereign_brain.db.models import Client
from sovereign_brain.db.repository import ClientRepository
from sovereign_brain.main import create_app

REQUEST = {"client_id": "C-1042", "question": "Summarise the exposure to energy stocks."}


class FakeClients:
    async def get(self, client_id: str) -> Client | None:
        return Client(id=client_id, name="Test Client", segment="wealth", risk_profile="moderate")


class FailingGraph:
    """Stands in for the graph and raises the given error."""

    def __init__(self, error: Exception) -> None:
        self.error = error

    async def ainvoke(self, *args, **kwargs):
        raise self.error


def post_with_failing_graph(error: Exception) -> httpx.Response:
    app = create_app()
    app.dependency_overrides[get_research_graph] = lambda: FailingGraph(error)
    app.dependency_overrides[ClientRepository] = FakeClients
    with TestClient(app, raise_server_exceptions=False) as client:
        return client.post("/v1/research", json=REQUEST)


def test_unreachable_model_is_503() -> None:
    response = post_with_failing_graph(ConnectionError("Failed to connect to Ollama"))

    assert response.status_code == 503
    assert response.json()["error"] == "model_unavailable"


def test_endless_agent_loop_is_508() -> None:
    response = post_with_failing_graph(GraphRecursionError("Recursion limit of 25 reached"))

    assert response.status_code == 508
    assert response.json()["error"] == "agent_loop_limit"


def test_unexpected_error_hides_the_details() -> None:
    response = post_with_failing_graph(RuntimeError("secret internal detail"))

    assert response.status_code == 500
    assert response.json() == {
        "error": "internal_error",
        "message": "Something went wrong on our side.",
        "details": None,
    }
