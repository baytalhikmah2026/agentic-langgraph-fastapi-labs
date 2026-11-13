import json

from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from sovereign_brain.api.v1.research import get_research_graph
from sovereign_brain.db.models import Client
from sovereign_brain.db.repository import ClientRepository
from sovereign_brain.graphs.hello import build_hello_graph
from sovereign_brain.main import create_app

FAKE_ANSWER = "Energy stocks are 12% of the portfolio."
REQUEST = {"client_id": "C-1042", "question": "Summarise the exposure to energy stocks."}


class FakeClients:
    async def get(self, client_id: str) -> Client | None:
        if client_id != "C-1042":
            return None
        return Client(id=client_id, name="Test Client", segment="wealth", risk_profile="moderate")


def read_events(text: str) -> list[tuple[str, object]]:
    """Turn an SSE body into a list of (event, data) pairs."""
    events = []
    for block in text.strip().split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        if "event" in fields:
            events.append((fields["event"], json.loads(fields["data"])))
    return events


def make_client() -> TestClient:
    app = create_app()
    graph = build_hello_graph(GenericFakeChatModel(messages=iter([AIMessage(FAKE_ANSWER)])))
    app.dependency_overrides[get_research_graph] = lambda: graph
    app.dependency_overrides[ClientRepository] = FakeClients
    return TestClient(app)


def test_stream_sends_start_nodes_tokens_and_done() -> None:
    with make_client() as client:
        response = client.post("/v1/research/stream", json=REQUEST)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = read_events(response.text)
    names = [name for name, _ in events]
    assert names[0] == "start"
    assert names[-1] == "done"
    assert ("node", {"node": "prepare_brief"}) in events
    assert ("node", {"node": "answer"}) in events
    tokens = "".join(data for name, data in events if name == "token")
    assert tokens == FAKE_ANSWER


def test_stream_for_an_unknown_client_is_404_before_streaming() -> None:
    with make_client() as client:
        response = client.post("/v1/research/stream", json={**REQUEST, "client_id": "C-9999"})

    assert response.status_code == 404
    assert response.json()["error"] == "not_found"
