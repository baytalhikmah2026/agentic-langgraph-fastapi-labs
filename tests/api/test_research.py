from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from sovereign_brain.api.v1.research import get_research_graph
from sovereign_brain.db.models import Client
from sovereign_brain.db.repository import ClientRepository
from sovereign_brain.graphs.hello import build_hello_graph
from sovereign_brain.main import create_app

FAKE_ANSWER = "Client C-1042 holds 12% of its portfolio in energy stocks."
KNOWN_CLIENT = Client(
    id="C-1042", name="Amina Rahman Holdings", segment="private-banking", risk_profile="moderate"
)


class FakeClients:
    """Stands in for ClientRepository: one known client, no database."""

    async def get(self, client_id: str) -> Client | None:
        return KNOWN_CLIENT if client_id == KNOWN_CLIENT.id else None


def make_client() -> TestClient:
    """The real application, with a fake model and a fake client register."""
    app = create_app()
    fake_model = GenericFakeChatModel(messages=iter([AIMessage(FAKE_ANSWER)]))
    graph = build_hello_graph(fake_model)
    app.dependency_overrides[get_research_graph] = lambda: graph
    app.dependency_overrides[ClientRepository] = FakeClients
    return TestClient(app)


def test_research_runs_the_graph() -> None:
    with make_client() as client:
        response = client.post(
            "/v1/research",
            json={"client_id": "c-1042", "question": "Summarise the exposure to energy stocks."},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["client_id"] == "C-1042"
    assert body["status"] == "completed"
    assert body["summary"] == FAKE_ANSWER
    assert len(body["request_id"]) == 32


def test_research_rejects_a_bad_request() -> None:
    with make_client() as client:
        response = client.post("/v1/research", json={"client_id": "X-1", "question": "short"})

    assert response.status_code == 422
    assert response.json()["error"] == "invalid_request"
    fields = [detail["field"] for detail in response.json()["details"]]
    assert fields == ["body.client_id", "body.question"]


def test_research_for_an_unknown_client_is_404() -> None:
    with make_client() as client:
        response = client.post(
            "/v1/research",
            json={"client_id": "C-9999", "question": "Summarise the exposure to energy stocks."},
        )

    assert response.status_code == 404
    assert response.json() == {
        "error": "not_found",
        "message": "Client C-9999 not found",
        "details": None,
    }
