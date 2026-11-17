"""The team endpoints (Labs 51, 52)."""

import json
from collections.abc import Callable

from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langchain_core.tools import StructuredTool

from sovereign_brain.api.v1.team import get_team_graph
from sovereign_brain.graphs.team.supervisor import build_team_graph


def read_events(text: str) -> list[tuple[str, object]]:
    """Turn an SSE body into a list of (event, data) pairs (as in test_stream.py)."""
    events = []
    for block in text.strip().split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        if "event" in fields:
            events.append((fields["event"], json.loads(fields["data"])))
    return events


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


async def read_note(name: str) -> str:
    """The full text of one research note."""
    return "Rating: hold."


def test_the_stream_shows_the_steps_inside_the_desk(
    app: FastAPI, client: TestClient, auth_headers: dict[str, str], make_model: Callable
) -> None:
    model = make_model(
        [
            delegate("research_desk", "d1"),
            AIMessage("The desk rates Gulf Petroleum hold."),  # the librarian
            AIMessage("Gulf Petroleum is rated hold."),  # the desk summary
            delegate("writer", "d2"),
            AIMessage("Gulf Petroleum is rated hold."),
            delegate("finish", "d3"),
        ]
    )
    note_tool = StructuredTool.from_function(coroutine=read_note, name="read_note")
    graph = build_team_graph(model, extra_tools=[note_tool])
    app.dependency_overrides[get_team_graph] = lambda: graph
    request = {"client_id": "C-1042", "question": "What do the notes say about Gulf Petroleum?"}

    response = client.post("/v1/team/stream", json=request, headers=auth_headers)

    events = read_events(response.text)
    assert ("node", {"path": ["research_desk"], "node": "summarise"}) in events
    assert ("answer", {"summary": "Gulf Petroleum is rated hold."}) in events
