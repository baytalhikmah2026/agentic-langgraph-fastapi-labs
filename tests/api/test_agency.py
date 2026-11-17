"""The Project Command Center (Lab 60): one call, one development cycle."""

from collections.abc import Callable

from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langchain_core.tools import StructuredTool

from sovereign_brain.api.v1.agency import get_agency_graph
from sovereign_brain.graphs.team.agency import build_agency_graph

SPEC = {
    "filename": "loss_percent.py",
    "purpose": "The loss of a sector shock as a percent of the portfolio.",
    "requirements": ["loss_percent(sector, total, shock) returns the loss in percent"],
    "check": 'print("PASS" if loss_percent(185000, 1000000, 40) == 7.4 else "FAIL")',
}
CODE = "def loss_percent(sector, total, shock):\n    return round(sector * shock / total, 1)\n"


async def write_file(name: str, text: str) -> str:
    """Create or replace one workspace file with the given text."""
    return f"Saved {name} ({len(text)} characters)"


async def sandbox(code: str) -> dict:
    return {"stdout": "PASS\n", "stderr": "", "exit_code": 0, "timed_out": False}


def test_one_call_runs_a_whole_cycle(
    app: FastAPI, client: TestClient, auth_headers: dict[str, str], make_model: Callable
) -> None:
    args = {"name": "loss_percent.py", "text": CODE}
    model = make_model(
        [
            AIMessage("", tool_calls=[{"name": "Spec", "args": SPEC, "id": "s1"}]),
            AIMessage("", tool_calls=[{"name": "write_file", "args": args, "id": "w1"}]),
            AIMessage("Written loss_percent.py."),
        ]
    )
    tools = [StructuredTool.from_function(coroutine=write_file, name="write_file")]
    graph = build_agency_graph(model, tools, run_code=sandbox)
    app.dependency_overrides[get_agency_graph] = lambda: graph
    request = {"request": "A function for the loss of a sector shock in percent."}

    response = client.post("/v1/agency", json=request, headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert (body["filename"], body["verdict"], body["rounds"]) == ("loss_percent.py", "passed", 1)
    assert body["test_output"] == "PASS\n"
