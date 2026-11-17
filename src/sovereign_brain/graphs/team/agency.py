"""The Software Development Agency (Lab 60, Module 6 milestone): PM, developer, reviewer.

The project manager turns a request into a Spec: a file name, requirements and a short check.
The developer writes the file into the project workspace through the workspace MCP server.
The reviewer runs the file together with the check in the sandbox (Lab 47) and sends the work
back with the test output until the check prints PASS, or the rounds run out.
"""

import logging
import operator
from collections.abc import Awaitable, Callable, Sequence
from typing import Annotated, TypedDict

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from pydantic import BaseModel, Field, ValidationError

from sovereign_brain.core.settings import get_settings
from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.trail import TrailEntry, mark
from sovereign_brain.tools.sandbox import CodeRequest, run_in_sandbox

logger = logging.getLogger("sovereign_brain.agency")

PM_PROMPT = (
    "You are the project manager of a small software team at Crescent Ledger Bank. Turn the "
    "request into a spec for ONE Python file with plain functions and no imports except math, "
    "statistics, decimal, fractions, datetime, json, itertools and collections. The check is a "
    "few Python lines that call the functions with example values, compare the results with "
    "the expected values, and print PASS only when every result is right."
)
DEVELOPER_PROMPT = (
    "You are the developer. Write the file from the spec with the write_file tool, then reply "
    "with one short sentence. Use only the allowed imports. Do not include the check in the file."
)

RunCode = Callable[[str], Awaitable[dict]]


class Spec(BaseModel):
    """The PM's spec: what to build, and how the reviewer will know it works."""

    filename: str = Field(pattern=r"^[a-z][a-z0-9_]*\.py$", max_length=60)
    purpose: str = Field(min_length=10, max_length=300)
    requirements: list[str] = Field(min_length=1, max_length=5)
    check: str = Field(min_length=10, max_length=1500, description="Python lines that print PASS")


class AgencyInput(TypedDict):
    request: str


class AgencyOutput(TypedDict):
    spec: dict
    verdict: str
    rounds: int
    test_output: str
    trail: list[TrailEntry]


class AgencyState(AgencyInput):
    spec: dict
    code: str  # overwritten: the file as the developer last wrote it
    rounds: int
    verdict: str  # passed, revise, gave_up or no_spec
    test_output: str  # overwritten: what the last test run printed
    trail: Annotated[list[TrailEntry], operator.add]


def written_code(messages: Sequence, filename: str) -> str:
    """The text of the last write_file call for the spec's file, from the developer's messages."""
    code = ""
    for message in messages:
        for call in getattr(message, "tool_calls", None) or []:
            if call["name"] == "write_file" and call["args"].get("name") == filename:
                code = call["args"].get("text", "")
    return code


def check_passed(result: dict) -> bool:
    """The check passed: the run finished normally, in time, and printed PASS."""
    finished = result.get("exit_code") == 0 and not result.get("timed_out")
    return finished and "PASS" in result.get("stdout", "")


async def sandbox_runner(code: str) -> dict:
    """The real runner: the sandbox container from Lab 47."""
    return await run_in_sandbox(code, get_settings().sandbox_url)


def build_agency_graph(
    model: BaseChatModel,
    workspace_tools: Sequence[BaseTool],
    run_code: RunCode = sandbox_runner,
) -> CompiledStateGraph:
    pm = model.with_structured_output(Spec)
    developer = create_agent(
        model,
        tools=list(workspace_tools),
        system_prompt=DEVELOPER_PROMPT,
        context_schema=ResearchContext,
        name="developer",
    )

    async def plan_work(state: AgencyState) -> dict:
        """The PM writes the spec; without a readable spec the agency stops politely."""
        try:
            spec = await pm.ainvoke([SystemMessage(PM_PROMPT), HumanMessage(state["request"])])
        except Exception as error:  # an unreadable spec ends the job, it never crashes it
            logger.warning("PM could not write a spec: %r", error)
            spec = None
        if not isinstance(spec, Spec):
            return {"verdict": "no_spec", "rounds": 0, "trail": mark("pm", "No readable spec")}
        note = f"Spec for {spec.filename}: {len(spec.requirements)} requirements"
        return {"spec": spec.model_dump(), "rounds": 0, "trail": mark("pm", note)}

    def after_plan(state: AgencyState) -> str:
        return "end" if state.get("verdict") == "no_spec" else "develop"

    async def develop(state: AgencyState, runtime: Runtime[ResearchContext]) -> dict:
        """The developer writes (or rewrites) the file through the workspace MCP server."""
        spec = state["spec"]
        request = (
            f"File: {spec['filename']}\nPurpose: {spec['purpose']}\nRequirements:\n"
            + "\n".join(f"- {r}" for r in spec["requirements"])
        )
        if state.get("verdict") == "revise":
            request += f"\nYour last version failed the check. Test output:\n{state['test_output']}"
        messages = {"messages": [HumanMessage(request)]}
        result = await developer.ainvoke(messages, context=runtime.context)
        code = written_code(result["messages"], spec["filename"]) or state.get("code", "")
        rounds = state["rounds"] + 1
        note = f"Round {rounds}: {spec['filename']} written ({len(code)} characters)"
        return {"code": code, "rounds": rounds, "trail": mark("developer", note)}

    async def review(state: AgencyState) -> dict:
        """The reviewer runs the file with the PM's check in the sandbox."""
        if not state["code"]:
            output = "The file was not written to the workspace."
            return {"verdict": "revise", "test_output": output, "trail": mark("reviewer", output)}
        try:
            checked = CodeRequest(code=f"{state['code']}\n\n{state['spec']['check']}")
        except ValidationError as error:  # the sandbox's first wall refused the code
            output = f"Refused before running: {error.errors()[0]['msg']}"
            return {"verdict": "revise", "test_output": output, "trail": mark("reviewer", output)}
        result = await run_code(checked.code)
        output = (result.get("stdout", "") + result.get("stderr", ""))[-1000:]
        verdict = "passed" if check_passed(result) else "revise"
        note = "Check printed PASS" if verdict == "passed" else "Check failed"
        return {"verdict": verdict, "test_output": output, "trail": mark("reviewer", note)}

    def after_review(state: AgencyState, runtime: Runtime[ResearchContext]) -> str:
        if state["verdict"] == "passed":
            return "end"
        return "give_up" if state["rounds"] > runtime.context.max_revisions else "develop"

    def give_up(state: AgencyState) -> dict:
        return {"verdict": "gave_up", "trail": mark("reviewer", "Out of rounds")}

    builder = StateGraph(
        AgencyState,
        context_schema=ResearchContext,
        input_schema=AgencyInput,
        output_schema=AgencyOutput,
    )
    builder.add_node("pm", plan_work)
    builder.add_node("developer", develop)
    builder.add_node("reviewer", review)
    builder.add_node("give_up", give_up)
    builder.add_edge(START, "pm")
    builder.add_conditional_edges("pm", after_plan, {"develop": "developer", "end": END})
    builder.add_edge("developer", "reviewer")
    builder.add_conditional_edges(
        "reviewer", after_review, {"end": END, "develop": "developer", "give_up": "give_up"}
    )
    builder.add_edge("give_up", END)
    return builder.compile(name="agency")
