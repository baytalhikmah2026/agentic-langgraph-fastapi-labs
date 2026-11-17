"""Team cases (Lab 54): saved by the network, read and briefed through the bridge."""

import json
from collections.abc import Callable

from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

from sovereign_brain.api.v1.cases import get_briefing_graph
from sovereign_brain.api.v1.team import get_network_graph
from sovereign_brain.graphs.team.briefing import build_briefing_graph
from sovereign_brain.graphs.team.network import build_network_graph

UNKNOWN_CASE = "0" * 32


def done_case_id(text: str) -> str:
    """The case ID from the stream's last event (done)."""
    last = text.strip().split("\n\n")[-1]
    data = next(line for line in last.splitlines() if line.startswith("data: "))
    return json.loads(data.removeprefix("data: "))["case_id"]


def test_a_case_is_saved_read_and_briefed(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    omar_headers: dict[str, str],
    make_model: Callable,
) -> None:
    shared = InMemorySaver()
    handoff = {"to": "writer", "reason": "The notes answer the question."}
    network = build_network_graph(
        make_model(
            [
                AIMessage("Energy is 18.5% of the portfolio."),
                AIMessage("", tool_calls=[{"name": "Handoff", "args": handoff, "id": "h1"}]),
                AIMessage("Energy is a modest 18.5% of the portfolio."),
            ]
        ),
        checkpointer=shared,
    )
    briefing = build_briefing_graph(
        make_model([AIMessage("Energy is 18.5% of the portfolio. No action needed.")]),
        checkpointer=shared,
    )
    app.dependency_overrides[get_network_graph] = lambda: network
    app.dependency_overrides[get_briefing_graph] = lambda: briefing
    request = {"client_id": "C-1042", "question": "How large is the energy exposure?"}
    stream = client.post("/v1/team/network", json=request, headers=auth_headers)
    case_id = done_case_id(stream.text)

    case = client.get(f"/v1/cases/{case_id}", headers=auth_headers)
    brief = client.post(f"/v1/cases/{case_id}/briefing", headers=auth_headers)
    stranger = client.get(f"/v1/cases/{case_id}", headers=omar_headers)

    assert case.status_code == 200
    assert case.json()["answer"] == "Energy is a modest 18.5% of the portfolio."
    assert brief.status_code == 200
    assert brief.json()["briefing"] == "Energy is 18.5% of the portfolio. No action needed."
    assert stranger.status_code == 404  # omar's namespace has no such case


def test_an_unknown_case_is_not_found(
    app: FastAPI, client: TestClient, auth_headers: dict[str, str], make_model: Callable
) -> None:
    network = build_network_graph(make_model([]), checkpointer=InMemorySaver())
    app.dependency_overrides[get_network_graph] = lambda: network

    response = client.get(f"/v1/cases/{UNKNOWN_CASE}", headers=auth_headers)

    assert response.status_code == 404
