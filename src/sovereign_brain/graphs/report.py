"""The report graph (Lab 49): a fixed protocol and a fixed answer shape.

Some answers must always follow the same steps and always have the same shape, because other
systems read them. This small graph forces both:
1. gather: the facts are always fetched first, by code; the model cannot skip this step.
2. draft: the model fills in a ResearchReport (structured output with Pydantic).
3. check: a guardrail compares the report with the facts; a wrong report goes back to draft
   with its problems listed, at most max_revisions times.
4. fallback: if it is still wrong (or there is nothing to report), the desk writes a plain
   report from the facts itself. Callers always receive a valid ResearchReport.
Lab 61: with an outbox, a fifth station, deliver, sends the finished report to the client.
The graph stops just before it (interrupt_before) and waits, saved by the checkpointer, until
a person releases it.
"""

import json
import logging
import operator
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime

from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.graphs.review import unsupported_figures
from sovereign_brain.graphs.trail import TrailEntry, mark
from sovereign_brain.schemas.report import ResearchReport, RiskLevel

logger = logging.getLogger("sovereign_brain.report")

REPORT_PROMPT = (
    "You write portfolio reports for the Research Desk of Crescent Ledger Bank. "
    "Use only the facts given, and copy every figure as it is written there. "
    "largest_sector is the first sector in the facts, with its percent. "
    "risk_level is high if that percent is above 50, medium if above 25, otherwise low. "
    "Write two to four key points, each with at least one figure from the facts."
)


class ReportInput(TypedDict):
    client_id: str
    client_profile: str


class ReportOutput(TypedDict):
    report: dict
    attempts: int
    checked: bool


class ReportState(ReportInput):
    facts: dict  # fetched by code in gather
    report: dict | None  # the latest draft, if it was a valid ResearchReport
    problems: list[str]  # what the guardrail found wrong with the latest draft
    attempts: int
    checked: bool
    verdict: Literal["done", "retry", "fallback"]
    delivered: str  # where the approved report was sent (Lab 61)
    trail: Annotated[list[TrailEntry], operator.add]


class ApprovalOutput(ReportOutput):
    """What an approval run returns: the report, and where it went once released (Lab 61)."""

    delivered: str


def sector_facts(portfolio: dict) -> dict:
    """The facts of a report: positions, total value and sectors, largest sector first."""
    holdings = portfolio["positions"]
    total = sum(h["market_value_usd"] for h in holdings)
    by_sector: dict[str, int] = {}
    for holding in holdings:
        sector, value = holding["sector"], holding["market_value_usd"]
        by_sector[sector] = by_sector.get(sector, 0) + value
    ranked = sorted(by_sector.items(), key=lambda item: (-item[1], item[0]))
    return {
        "client_id": portfolio["client_id"],
        "portfolio_value_usd": total,
        "positions": holdings,
        "sectors": [
            {"sector": sector, "value_usd": value, "percent": round(100 * value / total, 1)}
            for sector, value in ranked
        ],
    }


def risk_level(percent: float) -> RiskLevel:
    """The desk's concentration rule: how much sits in the largest sector."""
    if percent > 50:
        return "high"
    return "medium" if percent > 25 else "low"


def report_problems(report: ResearchReport, facts: dict) -> list[str]:
    """Everything in a report that does not match the facts; an empty list means correct."""
    problems = []
    top = facts["sectors"][0]
    if report.client_id != facts["client_id"]:
        problems.append(f"client_id must be {facts['client_id']}")
    if report.largest_sector != top["sector"]:
        problems.append(f"largest_sector must be {top['sector']}")
    if abs(report.largest_sector_percent - top["percent"]) > 0.05:
        problems.append(f"largest_sector_percent must be {top['percent']}")
    if report.risk_level != risk_level(top["percent"]):
        problems.append(f"risk_level must be {risk_level(top['percent'])}")
    text = " ".join([report.headline, *report.key_points])
    unsupported = unsupported_figures(text, json.dumps(facts))
    if unsupported:
        problems.append(f"these figures are not in the facts: {', '.join(unsupported)}")
    return problems


def fallback_report(client_id: str, facts: dict) -> ResearchReport:
    """A plain, always-valid report written by code from the facts alone."""
    if not facts["sectors"]:
        return ResearchReport(
            client_id=client_id,
            headline="No positions were found for this client.",
            largest_sector="none",
            largest_sector_percent=0,
            risk_level="low",
            key_points=["The register has no positions.", "Check the client's data load."],
        )
    top = facts["sectors"][0]
    return ResearchReport(
        client_id=client_id,
        headline=f"{top['sector']} is the largest sector at {top['percent']}% of the portfolio.",
        largest_sector=top["sector"],
        largest_sector_percent=top["percent"],
        risk_level=risk_level(top["percent"]),
        key_points=[
            f"Portfolio value: {facts['portfolio_value_usd']} USD.",
            f"{len(facts['positions'])} positions in {len(facts['sectors'])} sectors.",
        ],
    )


def report_brief(state: ReportState) -> str:
    """What the model reads: the client, the facts, and the problems of the last draft."""
    brief = (
        f"Client {state['client_id']} ({state['client_profile']}).\n"
        f"Facts (JSON): {json.dumps(state['facts'])}"
    )
    if state["problems"]:
        brief += (
            "\nYour previous report was sent back: "
            + "; ".join(state["problems"])
            + ". Fix these and write the report again."
        )
    return brief


async def gather(state: ReportState, runtime: Runtime[ResearchContext]) -> dict:
    """The forced first step: fetch the facts by code, every time."""
    facts = sector_facts(await runtime.context.portfolio.positions(state["client_id"]))
    note = f"Facts fetched: {len(facts['positions'])} positions in {len(facts['sectors'])} sectors"
    return {
        "facts": facts,
        "report": None,
        "problems": [],
        "attempts": 0,
        "checked": False,
        "trail": mark("gather", note),
    }


def after_gather(state: ReportState) -> Literal["draft", "fallback"]:
    return "draft" if state["facts"]["sectors"] else "fallback"


def check(state: ReportState, runtime: Runtime[ResearchContext]) -> dict:
    """The guardrail: a valid draft that matches the facts passes; anything else is sent back."""
    problems = list(state["problems"])
    if state["report"] is not None:
        problems = report_problems(ResearchReport.model_validate(state["report"]), state["facts"])
    if not problems:
        note = "Report matches the facts"
        return {"checked": True, "verdict": "done", "trail": mark("check", note)}
    listed = "; ".join(problems)
    if state["attempts"] > runtime.context.max_revisions:
        note = f"Still wrong after {state['attempts']} drafts: {listed}"
        return {"problems": problems, "verdict": "fallback", "trail": mark("check", note)}
    note = f"Sent back: {listed}"
    return {"problems": problems, "verdict": "retry", "trail": mark("check", note)}


def after_check(state: ReportState) -> Literal["done", "retry", "fallback"]:
    return state["verdict"]


def fallback(state: ReportState) -> dict:
    report = fallback_report(state["client_id"], state["facts"])
    note = "Plain report written from the facts"
    return {"report": report.model_dump(), "checked": False, "trail": mark("fallback", note)}


def deliver_to(outbox: Path) -> Callable[..., Awaitable[dict]]:
    """The deliver station for one outbox folder: one JSON file per released report."""

    async def deliver(state: ReportState, config: RunnableConfig) -> dict:
        approval_id = config["configurable"]["thread_id"].rpartition(":")[2]
        outbox.mkdir(parents=True, exist_ok=True)
        path = outbox / f"{approval_id}.json"
        letter = {
            "client_id": state["client_id"],
            "report": state["report"],
            "delivered_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        path.write_text(json.dumps(letter, indent=2), encoding="utf-8")
        return {"delivered": path.as_posix(), "trail": mark("deliver", f"Sent to {path.name}")}

    return deliver


def build_report_graph(
    model: BaseChatModel,
    checkpointer: BaseCheckpointSaver | None = None,
    outbox: Path | None = None,
) -> CompiledStateGraph:
    """Built once at start-up; each run brings its own ResearchContext (Lab 28).

    Lab 61: with an outbox, finished reports go to deliver, and the graph pauses before it.
    """
    structured = model.with_structured_output(ResearchReport)

    async def draft(state: ReportState) -> dict:
        """The model fills in a ResearchReport; anything that does not parse counts as wrong."""
        attempts = state["attempts"] + 1
        messages = [SystemMessage(REPORT_PROMPT), HumanMessage(report_brief(state))]
        try:
            report = await structured.ainvoke(messages)
        except Exception as error:  # broken JSON, missing fields, wrong types
            logger.warning("Report draft could not be parsed: %r", error)
            report = None
        if not isinstance(report, ResearchReport):
            return {
                "report": None,
                "problems": ["the reply was not a valid ResearchReport"],
                "attempts": attempts,
                "trail": mark("draft", f"Draft {attempts} was not a valid ResearchReport"),
            }
        return {
            "report": report.model_dump(),
            "problems": [],
            "attempts": attempts,
            "trail": mark("draft", f"Draft {attempts} written"),
        }

    builder = StateGraph(
        ReportState,
        context_schema=ResearchContext,
        input_schema=ReportInput,
        output_schema=ReportOutput if outbox is None else ApprovalOutput,
    )
    builder.add_node("gather", gather)
    builder.add_node("draft", draft)
    builder.add_node("check", check)
    builder.add_node("fallback", fallback)
    builder.add_edge(START, "gather")
    builder.add_conditional_edges(
        "gather", after_gather, {"draft": "draft", "fallback": "fallback"}
    )
    builder.add_edge("draft", "check")
    finished = END if outbox is None else "deliver"  # where a finished report goes
    builder.add_conditional_edges(
        "check", after_check, {"done": finished, "retry": "draft", "fallback": "fallback"}
    )
    builder.add_edge("fallback", finished)
    if outbox is None:
        return builder.compile(checkpointer=checkpointer, name="report")
    builder.add_node("deliver", deliver_to(outbox))
    builder.add_edge("deliver", END)
    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["deliver"],  # a person releases every report (Lab 61)
        name="approval",
    )
