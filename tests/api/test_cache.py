from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from sovereign_brain.api.v1.research import get_research_graph
from sovereign_brain.core.cache import ResearchCache
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
    graph = build_hello_graph(GenericFakeChatModel(messages=iter([AIMessage("First answer")])))
    app.dependency_overrides[get_research_graph] = lambda: graph
    app.dependency_overrides[ClientRepository] = FakeClients
    app.dependency_overrides[get_current_user] = lambda: TEST_ANALYST
    return TestClient(app)


def test_the_same_question_is_answered_from_the_cache() -> None:
    with make_client() as client:
        first = client.post("/v1/research", json=REQUEST).json()
        again = {**REQUEST, "question": "  SUMMARISE the exposure to energy   stocks. "}
        second = client.post("/v1/research", json=again).json()

    assert first["cached"] is False
    assert second["cached"] is True
    assert second["summary"] == "First answer"


def test_cache_keys_differ_per_client() -> None:
    question = "Summarise the exposure to energy stocks."

    assert ResearchCache.key("C-1042", question) != ResearchCache.key("C-2077", question)
    assert ResearchCache.key("C-1042", question).startswith("research:v1:")
