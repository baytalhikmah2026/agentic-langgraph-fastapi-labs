"""The red-team suite (Lab 79), run against the real app with a fake model."""

from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

from sovereign_brain.api.v1.approvals import get_approval_graph
from sovereign_brain.graphs.report import build_report_graph
from sovereign_brain.security.redteam import build_attacks, run_attacks

GOOD = {
    "client_id": "C-1042",
    "headline": "Financials make up 81.5% of the portfolio, a high concentration.",
    "largest_sector": "Financials",
    "largest_sector_percent": 81.5,
    "risk_level": "high",
    "key_points": ["Medina Bank is worth 815000 USD.", "Energy holdings total 185000 USD."],
}


def token(headers: dict[str, str]) -> str:
    return headers["Authorization"].removeprefix("Bearer ")


def test_every_attack_is_defended(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    omar_headers: dict[str, str],
    layla_headers: dict[str, str],
    yusuf_headers: dict[str, str],
    make_model: Callable,
    tmp_path: Path,
) -> None:
    reply = AIMessage("", tool_calls=[{"name": "ResearchReport", "args": GOOD, "id": "r1"}])
    graph = build_report_graph(make_model([reply]), checkpointer=InMemorySaver(), outbox=tmp_path)
    app.dependency_overrides[get_approval_graph] = lambda: graph
    approval_id = client.post("/v1/approvals/reports/C-1042", headers=auth_headers).json()[
        "approval_id"
    ]
    tokens = {
        "amina": token(auth_headers),
        "omar": token(omar_headers),
        "layla": token(layla_headers),
        "yusuf": token(yusuf_headers),
    }

    results = run_attacks(client, build_attacks(tokens, approval_id))

    opened = [f"{r.attack.name}: got {r.status}" for r in results if not r.passed]
    assert opened == []
    assert len(results) == 13
