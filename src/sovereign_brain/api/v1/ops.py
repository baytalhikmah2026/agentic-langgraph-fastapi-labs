"""Alerts from Grafana (Lab 69): the desk hears when something looks wrong."""

import logging
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

from sovereign_brain.core.settings import get_settings

router = APIRouter(prefix="/v1/ops", tags=["ops"])
logger = logging.getLogger("sovereign_brain.alerts")


class GrafanaAlert(BaseModel):
    """One alert inside a Grafana notification (other fields are ignored)."""

    status: str  # "firing" or "resolved"
    labels: dict[str, str] = {}
    annotations: dict[str, str] = {}


class GrafanaNotification(BaseModel):
    """What Grafana's webhook contact point sends."""

    status: str
    alerts: list[GrafanaAlert] = []


def alert_token(authorization: Annotated[str | None, Header()] = None) -> None:
    """Only Grafana knows this token (SB_ALERT_WEBHOOK_TOKEN)."""
    expected = f"Bearer {get_settings().alert_webhook_token.get_secret_value()}"
    if not secrets.compare_digest((authorization or "").encode(), expected.encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown alert sender")


@router.post(
    "/alerts", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(alert_token)]
)
async def receive_alerts(notification: GrafanaNotification) -> None:
    """Write every alert into the log, where the on-call person (and Lab 70) will see it."""
    for alert in notification.alerts:
        name = alert.labels.get("alertname", "unnamed alert")
        summary = alert.annotations.get("summary", "")
        logger.warning("Alert %s: %s. %s", alert.status, name, summary)
