from fastapi.testclient import TestClient

REQUEST = {"client_id": "C-1042", "question": "Summarise the exposure to energy stocks."}


def test_the_sixth_model_call_in_a_minute_is_refused(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    codes = [
        client.post("/v1/research", json=REQUEST, headers=auth_headers).status_code
        for _ in range(6)
    ]
    refused = client.post("/v1/research/stream", json=REQUEST, headers=auth_headers)

    assert codes == [200, 200, 200, 200, 200, 429]
    assert refused.status_code == 429
    assert refused.json()["error"] == "rate_limited"
