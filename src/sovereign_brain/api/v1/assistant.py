"""The Autonomous Research Assistant (Lab 50, Module 5 milestone): one request, the whole desk.

The assistant decides whether a request needs research (the research graph, with every tool:
portfolio, stress test, sandbox, and the MCP servers for notes, prices and reference data) or
a report (the report graph with its fixed protocol). It streams each step, tool call and tool
result as it happens, every event checked by Pydantic, and ends with the answer or report.
"""

import logging
import re
from collections.abc import AsyncIterator
from typing import Literal

from fastapi import APIRouter, Depends
from fastapi.sse import EventSourceResponse, ServerSentEvent
from langchain_core.messages import AIMessage, ToolMessage

from sovereign_brain.api.v1.reports import ReportGraph
from sovereign_brain.api.v1.research import (
    Checked,
    Registry,
    ResearchGraph,
    RunContext,
    mark_thread_used,
    run_config,
)
from sovereign_brain.core.errors import MODEL_ERRORS
from sovereign_brain.core.rate_limit import model_call_gate
from sovereign_brain.core.security import get_current_user
from sovereign_brain.schemas.assistant import (
    AnswerEvent,
    AssistantEvent,
    PlanEvent,
    ReportEvent,
    StepEvent,
    ToolCallEvent,
    ToolResultEvent,
)

router = APIRouter(
    prefix="/v1/assistant", tags=["assistant"], dependencies=[Depends(get_current_user)]
)
logger = logging.getLogger("sovereign_brain.assistant")

PREVIEW_CHARS = 200


def plan_mode(question: str) -> Literal["research", "report"]:
    """Research by default; a report when the analyst asks for one."""
    return "report" if re.search(r"\breports?\b", question.lower()) else "research"


def message_text(message: ToolMessage) -> str:
    """The text of a tool result: MCP tools answer with a list of content blocks."""
    if isinstance(message.content, list):
        return " ".join(
            block.get("text", "") for block in message.content if isinstance(block, dict)
        )
    return str(message.content)


def events_from_update(update: dict | None) -> list[AssistantEvent]:
    """Turn one station's update into events: its trail notes, tool calls and tool results."""
    if not update:
        return []
    events: list[AssistantEvent] = [
        StepEvent(station=entry["node"], note=entry["note"]) for entry in update.get("trail", [])
    ]
    for message in update.get("messages", []):
        if isinstance(message, AIMessage):
            events += [ToolCallEvent(tool=c["name"], args=c["args"]) for c in message.tool_calls]
        elif isinstance(message, ToolMessage):
            events.append(
                ToolResultEvent(
                    tool=message.name or "unknown",
                    ok=message.status != "error",
                    preview=message_text(message)[:PREVIEW_CHARS],
                )
            )
    return events


def sse(event: AssistantEvent) -> ServerSentEvent:
    return ServerSentEvent(event=event.type, data=event.model_dump(mode="json"))


@router.post("", response_class=EventSourceResponse, dependencies=[Depends(model_call_gate)])
async def assist(
    checked: Checked,
    research_graph: ResearchGraph,
    report_graph: ReportGraph,
    context: RunContext,
    registry: Registry,
) -> AsyncIterator[ServerSentEvent]:
    """Plan, work and report, streamed as Server-Sent Events."""
    mode = plan_mode(checked.body.question)
    yield sse(PlanEvent(mode=mode, thread_id=checked.thread_id))
    if mode == "report":
        graph = report_graph  # a report is a one-off: it keeps no conversation
        graph_input = {
            "client_id": checked.body.client_id,
            "client_profile": checked.graph_input["client_profile"],
        }
    else:
        await mark_thread_used(checked, context, registry)
        graph = research_graph
        graph_input = checked.graph_input
    final: dict = {}
    try:
        async for stream_mode, payload in graph.astream(
            graph_input,
            config=run_config(checked.thread_key),
            context=context,
            stream_mode=["updates", "values"],
        ):
            if stream_mode == "values":
                final = payload  # the output fields so far; the last one is the result
                continue
            for update in payload.values():
                for event in events_from_update(update):
                    yield sse(event)
    except MODEL_ERRORS as error:
        logger.error("AI model not available for the assistant: %r", error)
        yield ServerSentEvent(event="error", data={"error": "model_unavailable"})
        return
    if mode == "report":
        yield sse(ReportEvent(report=final["report"], checked=final["checked"]))
    else:
        yield sse(
            AnswerEvent(summary=final["answer"], route=final["route"], checked=final.get("checked"))
        )
    yield ServerSentEvent(event="done", data={"thread_id": checked.thread_id})
