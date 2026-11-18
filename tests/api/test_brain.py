"""The Sovereign Enterprise Brain (Labs 98-99): team, pause, four eyes, live channel, guards."""

import itertools

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from starlette.websockets import WebSocketDisconnect

from sovereign_brain.api.v1.brain import get_brain_graph
from sovereign_brain.capstone.graph import build_brain_graph
from sovereign_brain.core.settings import get_settings
from sovereign_brain.security.signing import verify

REQUEST = {"client_id": "C-1042", "question": "How big is this client's energy exposure?"}
DRAFT = AIMessage(
    "",
    tool_calls=[
        {
            "name": "AnalysisDraft",
            "args": {
                "summary": "Energy holdings are 185,000 USD of a 1,000,000 USD portfolio.",
                "figures": [{"label": "Energy holdings", "value": 185000, "unit": "USD"}],
                "risks": ["Oil price swings"],
                "confidence": 0.8,
            },
            "id": "draft-1",
        }
    ],
)


@pytest.fixture
def brain(app: FastAPI, make_model) -> None:
    graph = build_brain_graph(make_model(itertools.cycle([DRAFT])), checkpointer=InMemorySaver())
    app.dependency_overrides[get_brain_graph] = lambda: graph


def test_a_run_waits_for_a_second_person_and_is_sealed(
    client: TestClient,
    auth_headers: dict[str, str],
    omar_headers: dict[str, str],
    yusuf_headers: dict[str, str],
    brain: None,
) -> None:
    run = client.post("/v1/brain/runs", json=REQUEST, headers=auth_headers).json()
    own = client.post(
        f"/v1/brain/runs/{run['run_id']}/decision", json={"action": "approve"}, headers=auth_headers
    )
    done = client.post(
        f"/v1/brain/runs/{run['run_id']}/decision", json={"action": "approve"}, headers=omar_headers
    ).json()
    (entry,) = client.get("/v1/audit/events", headers=yusuf_headers).json()
    key = client.get("/v1/approvals/signing-key", headers=yusuf_headers).json()

    assert run["status"] == "awaiting_approval"
    assert [step.split(":")[0] for step in run["steps"]] == [
        "supervisor", "extraction", "supervisor", "sanitization", "supervisor", "analysis",
        "supervisor",
    ]
    assert run["problems"] == []  # 185,000 is Energy's total in the facts
    assert own.status_code == 403  # four eyes
    assert done["status"] == "delivered"
    assert entry["action"] == "brain.approved"
    statement = {k: v for k, v in entry["details"].items() if k != "signature"}
    assert verify(statement, entry["details"]["signature"], key["public_key_pem"])


def test_the_live_channel_streams_every_step(
    client: TestClient, auth_headers: dict[str, str], brain: None
) -> None:
    token = auth_headers["Authorization"].removeprefix("Bearer ")
    with client.websocket_connect("/v1/brain/ws") as socket:
        socket.send_json({"token": token})  # Lab 99: sign in with the first message
        socket.send_json(REQUEST)
        events = []
        while not events or events[-1]["type"] != "approval_needed":
            events.append(socket.receive_json())

    assert events[0]["type"] == "started"
    assert [e["agent"] for e in events if e["type"] == "agent"][:2] == ["supervisor", "extraction"]
    assert events[-1]["type"] == "approval_needed"


def test_the_live_channel_refuses_a_bad_token(client: TestClient, brain: None) -> None:
    with client.websocket_connect("/v1/brain/ws") as socket:
        socket.send_json({"token": "forged"})
        with pytest.raises(WebSocketDisconnect) as closed:
            socket.receive_json()

    assert closed.value.code == 1008  # policy violation


def test_a_narrow_sign_in_cannot_start_the_brain(
    client: TestClient, password: str, brain: None
) -> None:
    form = {"username": "amina", "password": password, "scope": "research:run"}
    token = client.post("/v1/auth/token", data=form).json()["access_token"]

    answer = client.post(
        "/v1/brain/runs", json=REQUEST, headers={"Authorization": f"Bearer {token}"}
    )

    assert answer.status_code == 403
    assert "brain:run" in answer.json()["message"]


def test_the_run_budget_stops_a_runaway_client(
    client: TestClient,
    auth_headers: dict[str, str],
    brain: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(get_settings(), "brain_run_limit", "1/hour")

    first = client.post("/v1/brain/runs", json=REQUEST, headers=auth_headers)
    second = client.post("/v1/brain/runs", json=REQUEST, headers=auth_headers)

    assert first.status_code == 200
    assert second.status_code == 429
