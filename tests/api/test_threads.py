from fastapi.testclient import TestClient

REQUEST = {"client_id": "C-1042", "question": "Summarise the exposure to energy stocks."}


def test_a_follow_up_continues_the_thread(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    first = {**REQUEST, "thread_id": "energy-review"}
    follow_up = {**first, "question": "And how does that compare with last year?"}

    one = client.post("/v1/research", json=first, headers=auth_headers).json()
    two = client.post("/v1/research", json=follow_up, headers=auth_headers).json()
    response = client.get("/v1/threads/energy-review", headers=auth_headers)

    assert one["thread_id"] == two["thread_id"] == "energy-review"
    assert two["cached"] is False
    assert response.status_code == 200
    thread = response.json()
    assert thread["turns"] == 2
    assert thread["messages"] == 5  # prompt, question, answer, question, answer
    assert thread["last_question"] == "And how does that compare with last year?"


def test_a_new_question_starts_a_new_thread(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    body = client.post("/v1/research", json=REQUEST, headers=auth_headers).json()

    assert len(body["thread_id"]) == 32
    thread = client.get(f"/v1/threads/{body['thread_id']}", headers=auth_headers).json()
    assert thread["turns"] == 1


def test_an_unknown_thread_is_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/v1/threads/nothing-here", headers=auth_headers)

    assert response.status_code == 404
    assert response.json()["message"] == "Thread nothing-here not found"


def test_the_conversation_can_be_read_back(
    client: TestClient, auth_headers: dict[str, str], fake_answer: str
) -> None:
    first = {**REQUEST, "thread_id": "read-back"}
    client.post("/v1/research", json=first, headers=auth_headers)
    client.post("/v1/research", json={**first, "question": "What is a bond?"}, headers=auth_headers)

    response = client.get("/v1/threads/read-back/messages", headers=auth_headers)

    assert response.status_code == 200
    messages = response.json()
    assert [m["type"] for m in messages] == ["human", "ai", "human", "ai"]
    assert messages[0]["content"].endswith("Summarise the exposure to energy stocks.")
    assert messages[1]["content"] == fake_answer
