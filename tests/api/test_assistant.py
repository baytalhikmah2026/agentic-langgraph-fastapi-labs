"""The Autonomous Research Assistant over the API (Lab 50, Module 5 milestone)."""

import json
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


def read_events(text: str) -> list[tuple[str, object]]:
    """Turn an SSE body into a list of (event, data) pairs (as in test_stream.py)."""
    events = []
    for block in text.strip().split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        if "event" in fields:
            events.append((fields["event"], json.loads(fields["data"])))
    return events


def test_a_question_is_researched_step_by_step(
    client: TestClient, auth_headers: dict[str, str], fake_answer: str
) -> None:
    request = {"client_id": "C-1042", "question": "Summarise the exposure to energy stocks."}

    response = client.post("/v1/assistant", json=request, headers=auth_headers)

    events = read_events(response.text)
    names = [name for name, _ in events]
    assert names[0] == "plan" and events[0][1]["mode"] == "research"
    step = {"type": "step", "station": "analyse", "note": "Draft answer written"}
    assert ("step", step) in events
    assert names[-2:] == ["answer", "done"]
    assert events[-2][1]["summary"] == fake_answer


def test_a_report_request_ends_with_a_validated_report(
    app: FastAPI, client: TestClient, auth_headers: dict[str, str], make_model: Callable
) -> None:
    reply = AIMessage("", tool_calls=[{"name": "ResearchReport", "args": GOOD, "id": "r1"}])
    app.dependency_overrides[get_report_graph] = lambda: build_report_graph(make_model([reply]))
    request = {"client_id": "C-1042", "question": "Write a portfolio report for this client."}

    response = client.post("/v1/assistant", json=request, headers=auth_headers)

    events = dict(read_events(response.text))  # the last event of each kind
    assert events["plan"]["mode"] == "report"
    assert events["report"] == {"type": "report", "report": GOOD, "checked": True}
