"""Health checks (Labs 3 and 86): alive, and ready to serve."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sovereign_brain.api.v1.health import readiness_checks
from sovereign_brain.main import create_app


def test_health_answers_ok() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "Sovereign Brain", "version": "0.2.0"}


def test_liveness_needs_nothing_but_the_process(client: TestClient) -> None:
    assert client.get("/health/live").json() == {"status": "alive"}


def test_readiness_checks_the_database_and_redis(app: FastAPI, client: TestClient) -> None:
    async def fine() -> None:
        return None

    app.dependency_overrides[readiness_checks] = lambda: {"database": fine, "redis": fine}
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "checks": {"database": "ok", "redis": "ok"}}


def test_a_pod_without_redis_is_not_ready(app: FastAPI, client: TestClient) -> None:
    async def fine() -> None:
        return None

    async def down() -> None:
        raise ConnectionError("Redis is not answering")

    app.dependency_overrides[readiness_checks] = lambda: {"database": fine, "redis": down}
    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["checks"] == {"database": "ok", "redis": "ConnectionError"}
