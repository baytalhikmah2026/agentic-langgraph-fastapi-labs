from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from sovereign_brain.api.v1.research import get_research_graph
from sovereign_brain.core.security import get_current_user
from sovereign_brain.db.models import Client, User
from sovereign_brain.db.repository import ClientRepository
from sovereign_brain.graphs.hello import build_hello_graph
from sovereign_brain.main import create_app

REQUEST = {"client_id": "C-1042", "question": "Summarise the exposure to energy stocks."}
TEST_ANALYST = User(username="test.analyst", full_name="Test Analyst", role="analyst")


class FakeClients:
    async def get(self, client_id: str) -> Client | None:
        return Client(id=client_id, name="Test Client", segment="wealth", risk_profile="moderate")


def make_client() -> TestClient:
    app = create_app()
    answers = iter([AIMessage(f"Answer {n}") for n in range(1, 7)])
    graph = build_hello_graph(GenericFakeChatModel(messages=answers))
    app.dependency_overrides[get_research_graph] = lambda: graph
    app.dependency_overrides[ClientRepository] = FakeClients
    app.dependency_overrides[get_current_user] = lambda: TEST_ANALYST
    return TestClient(app)


def test_the_sixth_model_call_in_a_minute_is_refused() -> None:
    with make_client() as client:
        codes = [client.post("/v1/research", json=REQUEST).status_code for _ in range(6)]
        refused = client.post("/v1/research/stream", json=REQUEST)

    assert codes == [200, 200, 200, 200, 200, 429]
    assert refused.status_code == 429
    assert refused.json()["error"] == "rate_limited"
