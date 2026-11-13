from fastapi.testclient import TestClient

from sovereign_brain.main import create_app


def test_health_answers_ok() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "Sovereign Brain", "version": "0.1.0"}
