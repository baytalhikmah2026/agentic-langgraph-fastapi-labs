"""The approval endpoints (Module 7): reports wait for a person before they are sent."""

from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

from sovereign_brain.api.v1.approvals import get_approval_graph
from sovereign_brain.graphs.report import build_report_graph

GOOD = {
    "client_id": "C-1042",
    "headline": "Financials make up 81.5% of the portfolio, a high concentration.",
    "largest_sector": "Financials",
    "largest_sector_percent": 81.5,
    "risk_level": "high",
    "key_points": ["Medina Bank is worth 815000 USD.", "Energy holdings total 185000 USD."],
}


def approval_app(app: FastAPI, make_model: Callable, outbox: Path, *replies: AIMessage) -> None:
    """The real approval graph with a fake model, a memory checkpointer and a test outbox."""
    graph = build_report_graph(make_model(replies), checkpointer=InMemorySaver(), outbox=outbox)
    app.dependency_overrides[get_approval_graph] = lambda: graph


def as_report(fields: dict, call_id: str) -> AIMessage:
    return AIMessage("", tool_calls=[{"name": "ResearchReport", "args": fields, "id": call_id}])


def test_a_requested_report_waits_for_approval(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    make_model: Callable,
    tmp_path: Path,
) -> None:
    approval_app(app, make_model, tmp_path, as_report(GOOD, "r1"))

    started = client.post("/v1/approvals/reports/C-1042", headers=auth_headers)
    approval_id = started.json()["approval_id"]
    status = client.get(f"/v1/approvals/{approval_id}", headers=auth_headers)

    assert started.status_code == 200
    assert status.json()["status"] == "awaiting_approval"
    assert status.json()["next"] == ["deliver"]
    assert status.json()["report"]["largest_sector"] == "Financials"


def test_an_unknown_approval_is_not_found(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    make_model: Callable,
    tmp_path: Path,
) -> None:
    approval_app(app, make_model, tmp_path)

    response = client.get(f"/v1/approvals/{'0' * 32}", headers=auth_headers)

    assert response.status_code == 404


def test_an_inspected_draft_continues_to_the_approval_line(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    make_model: Callable,
    tmp_path: Path,
) -> None:
    approval_app(app, make_model, tmp_path, as_report(GOOD, "r1"))

    started = client.post("/v1/approvals/reports/C-1042?inspect=draft", headers=auth_headers)
    approval_id = started.json()["approval_id"]
    continued = client.post(f"/v1/approvals/{approval_id}/continue", headers=auth_headers)
    again = client.post(f"/v1/approvals/{approval_id}/continue", headers=auth_headers)

    assert (started.json()["status"], started.json()["next"]) == ("paused", ["check"])
    assert continued.json()["status"] == "awaiting_approval"
    assert again.status_code == 409  # waiting for approval is not an inspection pause
