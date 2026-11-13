from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from sovereign_brain.api.v1.research import get_research_graph
from sovereign_brain.graphs.hello import build_hello_graph
from sovereign_brain.main import create_app

FAKE_ANSWER = "Client C-1042 holds 12% of its portfolio in energy stocks."


def make_client() -> TestClient:
    """The real application, with the graph running on a fake model instead of Ollama."""
    app = create_app()
    fake_model = GenericFakeChatModel(messages=iter([AIMessage(FAKE_ANSWER)]))
    graph = build_hello_graph(fake_model)
    app.dependency_overrides[get_research_graph] = lambda: graph
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
    fields = [error["loc"][-1] for error in response.json()["detail"]]
    assert fields == ["client_id", "question"]
