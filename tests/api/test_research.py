from fastapi.testclient import TestClient

REQUEST = {"client_id": "c-1042", "question": "Summarise the exposure to energy stocks."}


def test_research_runs_the_graph(
    client: TestClient, auth_headers: dict[str, str], fake_answer: str
) -> None:
    response = client.post("/v1/research", json=REQUEST, headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["client_id"] == "C-1042"
    assert body["status"] == "completed"
    assert body["summary"] == fake_answer
    assert body["route"] == "portfolio"
    assert body["checked"] is True
    assert body["request_id"] == response.headers["X-Request-ID"]


def test_research_rejects_a_bad_request(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/v1/research", json={"client_id": "X-1", "question": "short"}, headers=auth_headers
    )

    assert response.status_code == 422
    assert response.json()["error"] == "invalid_request"
    fields = [detail["field"] for detail in response.json()["details"]]
    assert fields == ["body.client_id", "body.question"]


def test_research_for_an_unknown_client_is_404(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/v1/research", json={**REQUEST, "client_id": "C-9999"}, headers=auth_headers
    )

    assert response.status_code == 404
    assert response.json()["message"] == "Client C-9999 not found"
