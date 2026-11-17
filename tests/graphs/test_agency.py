"""The software agency (Lab 60): spec, code into the workspace, check in the sandbox, repeat."""

from collections.abc import Callable
from unittest.mock import AsyncMock

from langchain_core.messages import AIMessage
from langchain_core.tools import StructuredTool

from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.team.agency import build_agency_graph
from sovereign_brain.graphs.trail import stations
from sovereign_brain.services.portfolio import PortfolioService

CONTEXT = ResearchContext(portfolio=AsyncMock(spec=PortfolioService), analyst="amina")
REQUEST = {"request": "A function that turns sector values into percentages of the total."}
SPEC = {
    "filename": "sector_weights.py",
    "purpose": "Turn sector values into percentages of the portfolio.",
    "requirements": ["weights(values) returns each sector's percent, rounded to 1 decimal"],
    "check": 'print("PASS" if weights({"Energy": 185000, "Financials": 815000}) == '
    '{"Energy": 18.5, "Financials": 81.5} else "FAIL")',
}
CODE = (
    "def weights(values):\n"
    "    total = sum(values.values())\n"
    "    return {name: round(100 * value / total, 1) for name, value in values.items()}\n"
)
PASSED = {"stdout": "PASS\n", "stderr": "", "exit_code": 0, "timed_out": False}
FAILED = {"stdout": "FAIL\n", "stderr": "", "exit_code": 0, "timed_out": False}


def workspace() -> tuple[dict[str, str], list[StructuredTool]]:
    """An in-memory stand-in for the workspace MCP server's write_file tool."""
    files: dict[str, str] = {}

    async def write_file(name: str, text: str) -> str:
        """Create or replace one workspace file with the given text."""
        files[name] = text
        return f"Saved {name} ({len(text)} characters)"

    return files, [StructuredTool.from_function(coroutine=write_file, name="write_file")]


def write(code: str, call_id: str) -> AIMessage:
    args = {"name": "sector_weights.py", "text": code}
    return AIMessage("", tool_calls=[{"name": "write_file", "args": args, "id": call_id}])


class Sandbox:
    """A stand-in for the sandbox: the listed results, one per run; it remembers the code."""

    def __init__(self, *results: dict) -> None:
        self.results = list(results)
        self.seen: list[str] = []

    async def __call__(self, code: str) -> dict:
        self.seen.append(code)
        return self.results.pop(0)


async def test_a_file_that_passes_the_check_is_done_in_one_round(make_model: Callable) -> None:
    files, tools = workspace()
    model = make_model(
        [
            AIMessage("", tool_calls=[{"name": "Spec", "args": SPEC, "id": "s1"}]),  # the PM
            write(CODE, "w1"),  # the developer writes through the workspace tool
            AIMessage("Written sector_weights.py."),
        ]
    )
    sandbox = Sandbox(PASSED)
    graph = build_agency_graph(model, tools, run_code=sandbox)

    result = await graph.ainvoke(REQUEST, context=CONTEXT)

    assert (result["verdict"], result["rounds"]) == ("passed", 1)
    assert files["sector_weights.py"] == CODE  # the file really is in the workspace
    assert sandbox.seen[0] == f"{CODE}\n\n{SPEC['check']}"  # the file and the check, together
    assert stations(result["trail"]) == ["pm", "developer", "reviewer"]


async def test_a_failed_check_goes_back_to_the_developer(make_model: Callable) -> None:
    _, tools = workspace()
    model = make_model(
        [
            AIMessage("", tool_calls=[{"name": "Spec", "args": SPEC, "id": "s1"}]),
            write(CODE.replace(", 1)", ", 0)"), "w1"),  # rounds to whole numbers: wrong
            AIMessage("Written."),
            write(CODE, "w2"),
            AIMessage("Fixed the rounding."),
        ]
    )
    graph = build_agency_graph(model, tools, run_code=Sandbox(FAILED, PASSED))

    result = await graph.ainvoke(REQUEST, context=CONTEXT)

    assert (result["verdict"], result["rounds"]) == ("passed", 2)
    assert stations(result["trail"]) == ["pm", "developer", "reviewer", "developer", "reviewer"]


async def test_without_a_readable_spec_the_agency_stops(make_model: Callable) -> None:
    _, tools = workspace()
    model = make_model([AIMessage("I would build a nice tool for you.")])  # no Spec
    graph = build_agency_graph(model, tools, run_code=Sandbox())

    result = await graph.ainvoke(REQUEST, context=CONTEXT)

    assert result["verdict"] == "no_spec"
