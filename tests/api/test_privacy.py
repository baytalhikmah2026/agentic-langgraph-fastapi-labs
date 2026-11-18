"""Privacy (Lab 78): a lead can erase one client's working data; analysts cannot."""

from fastapi.testclient import TestClient

QUESTION = {"client_id": "C-1042", "question": "Summarise the exposure to energy stocks."}


def test_a_lead_erases_a_clients_working_data(
    client: TestClient,
    auth_headers: dict[str, str],
    layla_headers: dict[str, str],
    yusuf_headers: dict[str, str],
) -> None:
    thread_id = client.post("/v1/research", json=QUESTION, headers=auth_headers).json()[
        "thread_id"
    ]

    first = client.post("/v1/privacy/erasure/C-1042", headers=layla_headers)
    again = client.post("/v1/privacy/erasure/C-1042", headers=layla_headers)
    history = client.get(f"/v1/threads/{thread_id}", headers=auth_headers)
    log = client.get("/v1/audit/events", headers=yusuf_headers).json()

    assert first.json() == {"threads": 1, "memories": 0, "cached_answers": 1}
    assert again.json() == {"threads": 0, "memories": 0, "cached_answers": 0}
    assert history.status_code == 404  # the conversation is gone
    assert (log[-1]["action"], log[-1]["subject"]) == ("privacy.erased", "C-1042")


def test_only_a_lead_may_erase(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post("/v1/privacy/erasure/C-1042", headers=auth_headers)
    policy = client.get("/v1/privacy/policy", headers=auth_headers)

    assert response.status_code == 403
    assert policy.status_code == 200
    assert policy.json()[-1]["kept_for"] == "10 years"
