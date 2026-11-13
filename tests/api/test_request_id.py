from fastapi.testclient import TestClient

from sovereign_brain.main import create_app


def test_a_new_id_is_created_and_returned() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health")

    request_id = response.headers["X-Request-ID"]
    assert len(request_id) == 32
    int(request_id, 16)  # 32 hexadecimal characters


def test_a_safe_incoming_id_is_kept() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health", headers={"X-Request-ID": "desk-7-req-0001"})

    assert response.headers["X-Request-ID"] == "desk-7-req-0001"


def test_an_unsafe_incoming_id_is_replaced() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health", headers={"X-Request-ID": "bad id with spaces!"})

    assert response.headers["X-Request-ID"] != "bad id with spaces!"
    assert len(response.headers["X-Request-ID"]) == 32
