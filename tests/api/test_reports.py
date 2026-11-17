"""The report endpoint (Lab 49): a strict ResearchReport for a client in the database."""

from collections.abc import Callable

from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from sovereign_brain.api.v1.reports import get_report_graph
from sovereign_brain.graphs.report import build_report_graph

GOOD = {
    "client_id": "C-1042",
    "headline": "Financials make up 81.5% of the portfolio, a high concentration.",
    "largest_sector": "Financials",
    "largest_sector_percent": 81.5,
    "risk_level": "high",
    "key_points": ["Medina Bank is worth 815000 USD.", "Energy holdings total 185000 USD."],
}


def test_a_report_comes_back_in_the_fixed_shape(
    app: FastAPI, client: TestClient, auth_headers: dict[str, str], make_model: Callable
) -> None:
    reply = AIMessage("", tool_calls=[{"name": "ResearchReport", "args": GOOD, "id": "r1"}])
    graph = build_report_graph(make_model([reply]))
    app.dependency_overrides[get_report_graph] = lambda: graph

    response = client.post("/v1/reports/c-1042", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["report"] == GOOD
    assert (body["attempts"], body["checked"]) == (1, True)


def test_a_report_for_an_unknown_client_is_404(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    assert client.post("/v1/reports/C-9999", headers=auth_headers).status_code == 404
