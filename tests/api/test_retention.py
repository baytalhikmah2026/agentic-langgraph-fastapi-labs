from fastapi.testclient import TestClient

REQUEST = {
    "client_id": "C-1042",
    "question": "Summarise the exposure to energy stocks.",
    "thread_id": "energy-review",
}


def test_every_run_registers_its_thread(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.post("/v1/research", json=REQUEST, headers=auth_headers)

    report = client.get("/v1/memory/retention", headers=auth_headers).json()

    assert report["ttl_minutes"] == 10080
    assert report["active_threads"] == 1
    assert report["expired_waiting"] == 0
    assert report["cleanups"] == 0


def test_the_cleanup_removes_unused_threads(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    client.post("/v1/research", json=REQUEST, headers=auth_headers)

    # older_than_minutes=0: every thread not used since this very moment counts as expired
    cleanup = client.post("/v1/memory/cleanup?older_than_minutes=0", headers=auth_headers)

    assert cleanup.json() == {"removed": 1}
    assert client.get("/v1/threads/energy-review", headers=auth_headers).status_code == 404
    report = client.get("/v1/memory/retention", headers=auth_headers).json()
    assert report["active_threads"] == 0
    assert report["cleanups"] == 1
    assert report["threads_removed"] == 1


def test_an_analyst_can_erase_a_thread(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.post("/v1/research", json=REQUEST, headers=auth_headers)

    first = client.delete("/v1/threads/energy-review", headers=auth_headers)
    second = client.delete("/v1/threads/energy-review", headers=auth_headers)

    assert first.status_code == 204
    assert second.status_code == 404
    report = client.get("/v1/memory/retention", headers=auth_headers).json()
    assert report["active_threads"] == 0
