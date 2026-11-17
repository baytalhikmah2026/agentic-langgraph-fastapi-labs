"""Correcting a question in an earlier checkpoint over the API (Lab 37)."""

from fastapi.testclient import TestClient

REQUEST = {"client_id": "C-1042", "question": "What is a bond?", "thread_id": "bond-basics"}


def test_a_question_can_be_corrected_at_an_earlier_checkpoint(
    client: TestClient, auth_headers: dict[str, str], fake_answer: str
) -> None:
    client.post("/v1/research", json=REQUEST, headers=auth_headers)
    history = client.get("/v1/threads/bond-basics/history", headers=auth_headers).json()
    after_intake = next(c for c in history if c["next"] == ["recall"])

    response = client.post(
        "/v1/threads/bond-basics/correct",
        json={"checkpoint_id": after_intake["checkpoint_id"], "question": "What is a share?"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["summary"] == fake_answer
    thread = client.get("/v1/threads/bond-basics", headers=auth_headers).json()
    assert thread["last_question"] == "What is a share?"
    assert thread["turns"] == 1
    after = client.get("/v1/threads/bond-basics/history", headers=auth_headers).json()
    assert "update" in [c["source"] for c in after]


def test_only_the_checkpoint_after_intake_can_be_corrected(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    client.post("/v1/research", json=REQUEST, headers=auth_headers)
    history = client.get("/v1/threads/bond-basics/history", headers=auth_headers).json()
    end_of_run = history[0]["checkpoint_id"]

    response = client.post(
        "/v1/threads/bond-basics/correct",
        json={"checkpoint_id": end_of_run, "question": "What is a share?"},
        headers=auth_headers,
    )

    assert response.status_code == 409
    assert response.json()["error"] == "conflict"
