import json

from fastapi.testclient import TestClient

REQUEST = {"client_id": "C-1042", "question": "Summarise the exposure to energy stocks."}


def read_events(text: str) -> list[tuple[str, object]]:
    """Turn an SSE body into a list of (event, data) pairs."""
    events = []
    for block in text.strip().split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        if "event" in fields:
            events.append((fields["event"], json.loads(fields["data"])))
    return events


def test_stream_sends_start_nodes_tokens_and_done(
    client: TestClient, auth_headers: dict[str, str], fake_answer: str
) -> None:
    response = client.post("/v1/research/stream", json=REQUEST, headers=auth_headers)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = read_events(response.text)
    names = [name for name, _ in events]
    assert names[0] == "start"
    assert names[-1] == "done"
    assert ("node", {"node": "intake"}) in events
    assert ("node", {"node": "classify"}) in events
    assert ("node", {"node": "analyse"}) in events
    tokens = "".join(data for name, data in events if name == "token")
    assert tokens == fake_answer


def test_stream_for_an_unknown_client_is_404_before_streaming(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/v1/research/stream", json={**REQUEST, "client_id": "C-9999"}, headers=auth_headers
    )

    assert response.status_code == 404
    assert response.json()["error"] == "not_found"
