"""The approval endpoints (Module 7): reports wait for a person before they are sent."""

import json
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


def test_a_second_analyst_approves_and_the_report_is_sent(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    omar_headers: dict[str, str],
    make_model: Callable,
    tmp_path: Path,
) -> None:
    approval_app(app, make_model, tmp_path, as_report(GOOD, "r1"))
    approval_id = client.post("/v1/approvals/reports/C-1042", headers=auth_headers).json()[
        "approval_id"
    ]

    waiting = client.get("/v1/approvals", headers=omar_headers).json()
    decided = client.post(
        f"/v1/approvals/{approval_id}/decision", json={"action": "approve"}, headers=omar_headers
    )

    assert [(w["approval_id"], w["requested_by"]) for w in waiting] == [(approval_id, "amina")]
    assert decided.json()["status"] == "delivered"
    assert (tmp_path / f"{approval_id}.json").exists()
    assert client.get("/v1/approvals", headers=omar_headers).json() == []


def test_nobody_approves_their_own_report(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    make_model: Callable,
    tmp_path: Path,
) -> None:
    approval_app(app, make_model, tmp_path, as_report(GOOD, "r1"))
    approval_id = client.post("/v1/approvals/reports/C-1042", headers=auth_headers).json()[
        "approval_id"
    ]

    decided = client.post(
        f"/v1/approvals/{approval_id}/decision", json={"action": "approve"}, headers=auth_headers
    )

    assert decided.status_code == 403  # four eyes: a second person must decide
    assert list(tmp_path.iterdir()) == []


def test_a_rejected_report_stays_unsent(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    omar_headers: dict[str, str],
    make_model: Callable,
    tmp_path: Path,
) -> None:
    approval_app(app, make_model, tmp_path, as_report(GOOD, "r1"))
    approval_id = client.post("/v1/approvals/reports/C-1042", headers=auth_headers).json()[
        "approval_id"
    ]
    decision = {"action": "reject", "comment": "Please add the bond holdings."}

    rejected = client.post(
        f"/v1/approvals/{approval_id}/decision", json=decision, headers=omar_headers
    )
    again = client.post(
        f"/v1/approvals/{approval_id}/decision", json={"action": "approve"}, headers=omar_headers
    )

    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["trail"][-1]["note"] == "Rejected by omar: Please add the bond holdings."
    assert list(tmp_path.iterdir()) == []
    assert again.status_code == 409  # a decided report stays decided


def test_feedback_brings_back_a_new_draft(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    omar_headers: dict[str, str],
    make_model: Callable,
    tmp_path: Path,
) -> None:
    better = {**GOOD, "headline": "Medina Bank alone is 81.5% of the portfolio."}
    approval_app(app, make_model, tmp_path, as_report(GOOD, "r1"), as_report(better, "r2"))
    approval_id = client.post("/v1/approvals/reports/C-1042", headers=auth_headers).json()[
        "approval_id"
    ]

    response = client.post(
        f"/v1/approvals/{approval_id}/feedback",
        json={"comment": "Name the bank in the headline."},
        headers=omar_headers,
    )

    body = response.json()
    assert body["status"] == "awaiting_approval"
    assert body["feedback"] == ["omar: Name the bank in the headline."]
    assert body["report"]["headline"] == better["headline"]
    assert [step["note"] for step in body["trail"]][-3:] == [
        "Sent back by omar: Name the bank in the headline.",
        "Draft 2 written",
        "Report matches the facts",
    ]


def test_the_requester_cannot_send_back_their_own_report(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    make_model: Callable,
    tmp_path: Path,
) -> None:
    approval_app(app, make_model, tmp_path, as_report(GOOD, "r1"))
    approval_id = client.post("/v1/approvals/reports/C-1042", headers=auth_headers).json()[
        "approval_id"
    ]

    response = client.post(
        f"/v1/approvals/{approval_id}/feedback",
        json={"comment": "Looks fine."},
        headers=auth_headers,
    )

    assert response.status_code == 403


def test_a_lead_edits_and_a_second_person_approves(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    omar_headers: dict[str, str],
    layla_headers: dict[str, str],
    make_model: Callable,
    tmp_path: Path,
) -> None:
    approval_app(app, make_model, tmp_path, as_report(GOOD, "r1"))
    approval_id = client.post("/v1/approvals/reports/C-1042", headers=auth_headers).json()[
        "approval_id"
    ]
    edited = {**GOOD, "headline": "Medina Bank is 81.5% of the portfolio: reduce it."}
    change = {"mode": "edit", "report": edited, "reason": "Make the advice clear."}

    overridden = client.post(
        f"/v1/approvals/{approval_id}/override", json=change, headers=layla_headers
    )
    by_layla = client.post(
        f"/v1/approvals/{approval_id}/decision", json={"action": "approve"}, headers=layla_headers
    )
    by_omar = client.post(
        f"/v1/approvals/{approval_id}/decision", json={"action": "approve"}, headers=omar_headers
    )

    assert overridden.json()["status"] == "awaiting_approval"
    assert overridden.json()["overridden_by"] == "layla"
    assert by_layla.status_code == 403  # nobody clears their own changes
    assert by_omar.json()["status"] == "delivered"
    letter = json.loads((tmp_path / f"{approval_id}.json").read_text(encoding="utf-8"))
    assert letter["report"] == edited


def test_only_a_lead_can_override(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    omar_headers: dict[str, str],
    make_model: Callable,
    tmp_path: Path,
) -> None:
    approval_app(app, make_model, tmp_path, as_report(GOOD, "r1"))
    approval_id = client.post("/v1/approvals/reports/C-1042", headers=auth_headers).json()[
        "approval_id"
    ]
    change = {"mode": "fallback", "reason": "I prefer the plain report."}

    response = client.post(
        f"/v1/approvals/{approval_id}/override", json=change, headers=omar_headers
    )

    assert response.status_code == 403


def test_an_edited_report_must_match_the_facts(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    layla_headers: dict[str, str],
    make_model: Callable,
    tmp_path: Path,
) -> None:
    approval_app(app, make_model, tmp_path, as_report(GOOD, "r1"))
    approval_id = client.post("/v1/approvals/reports/C-1042", headers=auth_headers).json()[
        "approval_id"
    ]
    change = {"mode": "edit", "report": {**GOOD, "largest_sector_percent": 80}, "reason": "Round"}

    response = client.post(
        f"/v1/approvals/{approval_id}/override", json=change, headers=layla_headers
    )

    assert response.status_code == 422
    assert response.json()["detail"] == ["largest_sector_percent must be 81.5"]


def test_a_lead_switches_to_the_fallback_report(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    layla_headers: dict[str, str],
    make_model: Callable,
    tmp_path: Path,
) -> None:
    approval_app(app, make_model, tmp_path, as_report(GOOD, "r1"))
    approval_id = client.post("/v1/approvals/reports/C-1042", headers=auth_headers).json()[
        "approval_id"
    ]
    change = {"mode": "fallback", "reason": "Use the plain wording for this client."}

    response = client.post(
        f"/v1/approvals/{approval_id}/override", json=change, headers=layla_headers
    )

    body = response.json()
    assert body["status"] == "awaiting_approval"
    assert body["checked"] is False  # the plain report is written by code, not checked
    assert [step["node"] for step in body["trail"]][-2:] == ["check", "fallback"]
