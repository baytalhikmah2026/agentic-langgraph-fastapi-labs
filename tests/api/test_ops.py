"""Grafana alerts (Lab 69): only the right token gets in, and every alert is logged."""

import logging

import pytest
from fastapi.testclient import TestClient

from sovereign_brain.core.settings import get_settings

NOTIFICATION = {
    "status": "firing",
    "alerts": [
        {
            "status": "firing",
            "labels": {"alertname": "Runs that will not stop", "severity": "warning"},
            "annotations": {"summary": "A graph is running more than 12 stations per run"},
            "fingerprint": "6a1e9c4d2b7f4e08",
        }
    ],
}


def test_alerts_need_the_webhook_token(client: TestClient) -> None:
    response = client.post(
        "/v1/ops/alerts", json=NOTIFICATION, headers={"Authorization": "Bearer guess"}
    )

    assert response.status_code == 401


def test_an_alert_is_written_to_the_log(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    token = get_settings().alert_webhook_token.get_secret_value()

    with caplog.at_level(logging.WARNING, logger="sovereign_brain.alerts"):
        response = client.post(
            "/v1/ops/alerts", json=NOTIFICATION, headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 204
    assert "Alert firing: Runs that will not stop." in caplog.text
