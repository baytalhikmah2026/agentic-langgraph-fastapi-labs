from fastapi.testclient import TestClient

from sovereign_brain.core.cache import ResearchCache

REQUEST = {"client_id": "C-1042", "question": "Summarise the exposure to energy stocks."}


def test_the_same_question_is_answered_from_the_cache(
    client: TestClient, auth_headers: dict[str, str], in_memory_cache: dict[str, str]
) -> None:
    first = client.post("/v1/research", json=REQUEST, headers=auth_headers).json()
    again = {**REQUEST, "question": "  SUMMARISE the exposure to energy   stocks. "}
    second = client.post("/v1/research", json=again, headers=auth_headers).json()

    assert first["cached"] is False
    assert second["cached"] is True
    assert second["summary"] == first["summary"]
    assert len(in_memory_cache) == 1


def test_cache_keys_differ_per_client() -> None:
    question = "Summarise the exposure to energy stocks."

    assert ResearchCache.key("C-1042", question) != ResearchCache.key("C-2077", question)
    assert ResearchCache.key("C-1042", question).startswith("research:v1:")
