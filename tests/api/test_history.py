"""Thread history and rewind over the API (Lab 36)."""

from fastapi.testclient import TestClient

REQUEST = {"client_id": "C-1042", "question": "What is a bond?", "thread_id": "bond-basics"}


def test_the_history_lists_every_checkpoint(
    client: TestClient, auth_headers: dict[str, str], fake_answer: str
) -> None:
    client.post("/v1/research", json=REQUEST, headers=auth_headers)

    response = client.get("/v1/threads/bond-basics/history", headers=auth_headers)

    assert response.status_code == 200
    history = response.json()
    assert [c["step"] for c in history] == [3, 2, 1, 0, -1]
    assert history[0]["next"] == []
    assert history[0]["answer"] == fake_answer
    assert history[0]["parent_checkpoint_id"] == history[1]["checkpoint_id"]
    assert history[-1]["source"] == "input"


def test_a_thread_can_be_rewound(
    client: TestClient, auth_headers: dict[str, str], fake_answer: str
) -> None:
    client.post("/v1/research", json=REQUEST, headers=auth_headers)
    history = client.get("/v1/threads/bond-basics/history", headers=auth_headers).json()
    before_explain = next(c for c in history if c["next"] == ["explain"])

    response = client.post(
        "/v1/threads/bond-basics/rewind",
        json={"checkpoint_id": before_explain["checkpoint_id"]},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["summary"] == fake_answer
    after = client.get("/v1/threads/bond-basics/history", headers=auth_headers).json()
    assert "fork" in [c["source"] for c in after]
    thread = client.get("/v1/threads/bond-basics", headers=auth_headers).json()
    assert thread["messages"] == 3  # prompt, question, the new answer


def test_an_unknown_checkpoint_is_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.post("/v1/research", json=REQUEST, headers=auth_headers)

    response = client.post(
        "/v1/threads/bond-basics/rewind",
        json={"checkpoint_id": "not-a-checkpoint"},
        headers=auth_headers,
    )

    assert response.status_code == 404
    expected = "Checkpoint not-a-checkpoint not found in thread bond-basics"
    assert response.json()["message"] == expected
