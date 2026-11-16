from fastapi.testclient import TestClient

REQUEST = {"client_id": "C-1042", "question": "Summarise the exposure to energy stocks."}


def test_the_trace_lists_every_station_in_order(
    client: TestClient, auth_headers: dict[str, str], fake_answer: str
) -> None:
    response = client.post("/v1/research/trace", json=REQUEST, headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["summary"] == fake_answer
    assert [step["node"] for step in body["trail"]] == ["intake", "classify", "analyse", "review"]
    assert body["trail"][0]["note"] == "Request received for C-1042 from amina"
    # The API asks the model router; the fake model gives no decision, so the rules decide
    assert body["trail"][1]["note"] == "Route: portfolio (rules fallback)"
    times = [step["at"] for step in body["trail"]]
    assert times == sorted(times)


def test_the_trace_is_never_cached(
    client: TestClient, auth_headers: dict[str, str], in_memory_cache: dict[str, dict]
) -> None:
    response = client.post("/v1/research/trace", json=REQUEST, headers=auth_headers)

    assert response.status_code == 200
    assert in_memory_cache == {}
