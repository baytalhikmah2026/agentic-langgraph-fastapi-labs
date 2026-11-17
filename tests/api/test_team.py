"""The team endpoint (Lab 51)."""

from collections.abc import Callable

from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from sovereign_brain.api.v1.team import get_team_graph
from sovereign_brain.graphs.team.supervisor import build_team_graph


def delegate(next_worker: str, call_id: str) -> AIMessage:
    args = {"next": next_worker, "task": "Your part, please."}
    return AIMessage("", tool_calls=[{"name": "Delegation", "args": args, "id": call_id}])


def test_the_team_answers_with_its_notes_and_trail(
    app: FastAPI, client: TestClient, auth_headers: dict[str, str], make_model: Callable
) -> None:
    model = make_model(
        [
            delegate("analyst", "d1"),
            AIMessage("Energy is a modest part of the portfolio."),
            delegate("writer", "d2"),
            AIMessage("The energy exposure is modest."),
            delegate("finish", "d3"),
        ]
    )
    graph = build_team_graph(model)
    app.dependency_overrides[get_team_graph] = lambda: graph
    request = {"client_id": "C-1042", "question": "How large is the energy exposure?"}

    response = client.post("/v1/team", json=request, headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["summary"] == "The energy exposure is modest."
    assert [note["author"] for note in body["notes"]] == ["analyst"]
    assert [step["node"] for step in body["trail"]] == [
        "supervisor", "analyst", "supervisor", "writer", "supervisor",
    ]
