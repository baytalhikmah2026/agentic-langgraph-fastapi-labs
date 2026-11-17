"""The Plan-and-Execute pattern (Lab 56): a planner writes the flight plan, an executor flies it.

The planner breaks a long task into a few short steps. The executor works through them one by
one with its tools. When a step fails, the planner writes a new plan for the rest of the trip,
knowing what has been done and what went wrong. A limit on replanning keeps every trip finite,
and the finish station always answers from the steps that were completed.
"""

import logging
import operator
from collections.abc import Sequence
from typing import Annotated, Literal, TypedDict

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from pydantic import BaseModel, Field

from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.team.state import TeamInput
from sovereign_brain.graphs.trail import TrailEntry, mark
from sovereign_brain.tools.portfolio import PORTFOLIO_TOOLS
from sovereign_brain.tools.risk import RISK_TOOLS

logger = logging.getLogger("sovereign_brain.team")

PLANNER_PROMPT = (
    "You plan research tasks at Crescent Ledger Bank. Break the task into at most five short "
    "steps, in order. Each step is one thing an analyst with portfolio and risk tools can do. "
    "Do not include a step for writing the final answer."
)
REPLANNER_PROMPT = (
    "A step of the plan failed. Write a new plan for the rest of the task only, using what the "
    "completed steps found and avoiding what failed. At most five short steps."
)
EXECUTOR_PROMPT = (
    "You carry out one step of a research plan with your tools, and reply with a short result "
    "that quotes only figures the tools returned. If you cannot complete the step with your "
    "tools, reply with FAILED: and the reason."
)
FINISH_PROMPT = (
    "Answer the client question in at most three sentences, using only the results of the "
    "completed steps and their figures."
)
FALLBACK_PLAN = ["Collect the portfolio facts needed for the question."]


class PlanStep(BaseModel):
    goal: str = Field(min_length=5, max_length=200, description="One short step, as an order")


class Plan(BaseModel):
    """The flight plan: a few steps, in the order they are done."""

    steps: list[PlanStep] = Field(min_length=1, max_length=5)


class StepResult(TypedDict):
    step: int
    goal: str
    status: Literal["done", "failed"]
    result: str


class PlannerOutput(TypedDict):
    answer: str
    completed: list[StepResult]


class PlannerState(TeamInput):
    plan: list[str]  # overwritten: the steps still to do, first one next
    completed: Annotated[list[StepResult], operator.add]  # appended: every step flown
    replans: int
    answer: str
    trail: Annotated[list[TrailEntry], operator.add]


def progress(state: PlannerState) -> str:
    """What the planner and the finish station read: the task and every step so far."""
    lines = [f"Client {state['client_id']} ({state['client_profile']}): {state['question']}"]
    for done in state.get("completed", []):
        lines.append(f"Step {done['step']} ({done['status']}): {done['goal']} -> {done['result']}")
    return "\n".join(lines)


def build_planner_graph(
    model: BaseChatModel, extra_tools: Sequence[BaseTool] = ()
) -> CompiledStateGraph:
    planner = model.with_structured_output(Plan)
    executor = create_agent(
        model,
        tools=[*PORTFOLIO_TOOLS, *RISK_TOOLS, *extra_tools],
        system_prompt=EXECUTOR_PROMPT,
        context_schema=ResearchContext,
        name="executor",
    )

    async def ask_planner(prompt: str, state: PlannerState) -> list[str]:
        """A plan from the model, or the one-step fallback if it cannot be read."""
        try:
            plan = await planner.ainvoke([SystemMessage(prompt), HumanMessage(progress(state))])
        except Exception as error:  # a broken plan must never stop the trip
            logger.warning("Planner failed, using the fallback plan: %r", error)
            plan = None
        if not isinstance(plan, Plan):
            return list(FALLBACK_PLAN)
        return [step.goal for step in plan.steps]

    async def make_plan(state: PlannerState) -> dict:
        steps = await ask_planner(PLANNER_PROMPT, state)
        return {"plan": steps, "replans": 0, "trail": mark("plan", f"{len(steps)} steps planned")}

    async def execute(state: PlannerState, runtime: Runtime[ResearchContext]) -> dict:
        """Fly the next step of the plan, and note how it went."""
        goal, number = state["plan"][0], len(state.get("completed", [])) + 1
        request = f"{progress(state)}\nYour step: {goal}"
        messages = {"messages": [HumanMessage(request)]}
        result = await executor.ainvoke(messages, context=runtime.context)
        reply = str(result["messages"][-1].content).strip()
        status = "failed" if reply.upper().startswith("FAILED") or not reply else "done"
        done: StepResult = {"step": number, "goal": goal, "status": status, "result": reply}
        return {
            "plan": state["plan"][1:],
            "completed": [done],
            "trail": mark("execute", f"Step {number} {status}: {goal}"),
        }

    def after_execute(state: PlannerState, runtime: Runtime[ResearchContext]) -> str:
        if state["completed"][-1]["status"] == "failed":
            return "replan" if state["replans"] < runtime.context.max_replans else "finish"
        return "execute" if state["plan"] else "finish"

    async def replan(state: PlannerState) -> dict:
        steps = await ask_planner(REPLANNER_PROMPT, state)
        note = f"New plan, {len(steps)} steps"
        return {"plan": steps, "replans": state["replans"] + 1, "trail": mark("replan", note)}

    async def finish(state: PlannerState) -> dict:
        reply = await model.ainvoke([SystemMessage(FINISH_PROMPT), HumanMessage(progress(state))])
        return {"answer": str(reply.content), "trail": mark("finish", "Answer written")}

    builder = StateGraph(
        PlannerState,
        context_schema=ResearchContext,
        input_schema=TeamInput,
        output_schema=PlannerOutput,
    )
    builder.add_node("plan", make_plan)
    builder.add_node("execute", execute)
    builder.add_node("replan", replan)
    builder.add_node("finish", finish)
    builder.add_edge(START, "plan")
    builder.add_edge("plan", "execute")
    builder.add_conditional_edges(
        "execute", after_execute, {"execute": "execute", "replan": "replan", "finish": "finish"}
    )
    builder.add_edge("replan", "execute")
    builder.add_edge("finish", END)
    return builder.compile(name="planner")
