"""Research requests: the main counter of the Research Desk."""

import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.sse import EventSourceResponse, ServerSentEvent
from langchain_core.messages import AIMessageChunk
from langgraph.graph.state import CompiledStateGraph

from sovereign_brain.core.cache import Cache
from sovereign_brain.core.errors import MODEL_ERRORS
from sovereign_brain.core.rate_limit import model_call_gate
from sovereign_brain.core.request_id import get_request_id
from sovereign_brain.core.security import CurrentUser, get_current_user
from sovereign_brain.core.settings import get_settings
from sovereign_brain.db.repository import Clients
from sovereign_brain.graphs.context import ResearchContext
from sovereign_brain.memory.semantic import SemanticMemory
from sovereign_brain.memory.summaries import ThreadArchivist
from sovereign_brain.memory.retention import ThreadRegistry
from sovereign_brain.memory.threads import thread_config, thread_key
from sovereign_brain.schemas.research import ResearchRequest, ResearchResponse, ResearchTrace
from sovereign_brain.services.portfolio import PortfolioService

router = APIRouter(
    prefix="/v1/research", tags=["research"], dependencies=[Depends(get_current_user)]
)
logger = logging.getLogger("sovereign_brain.research")
# The output fields plus the audit trail: what the trace endpoint asks the graph for (Lab 26)
TRACE_KEYS = ["answer", "route", "checked", "trail"]
# The stations whose words are the answer; the router's model call is not streamed (Lab 30)
ANSWER_NODES = {"analyse", "explain"}


def get_research_graph(request: Request) -> CompiledStateGraph:
    """The graph built once at start-up (see lifespan in main.py)."""
    return request.app.state.research_graph


ResearchGraph = Annotated[CompiledStateGraph, Depends(get_research_graph)]


def get_portfolio(request: Request) -> PortfolioService:
    """The portfolio service created at start-up (see lifespan in main.py)."""
    return request.app.state.portfolio


def get_memory(request: Request) -> SemanticMemory | None:
    """Semantic memory created at start-up, or None when it is switched off (Lab 38)."""
    return request.app.state.memory


Memory = Annotated[SemanticMemory | None, Depends(get_memory)]


def get_archivist(request: Request) -> ThreadArchivist | None:
    """Summarises threads into semantic memory; None when memory is switched off (Lab 40)."""
    return request.app.state.archivist


Archivist = Annotated[ThreadArchivist | None, Depends(get_archivist)]


def research_context(
    user: CurrentUser,
    portfolio: Annotated[PortfolioService, Depends(get_portfolio)],
    memory: Memory,
) -> ResearchContext:
    """What this run brings along: the services, the signed-in analyst, today's limits."""
    settings = get_settings()
    return ResearchContext(
        portfolio=portfolio,
        analyst=user.username,
        max_revisions=settings.max_revisions,
        router=settings.research_router,
        memory=memory,
        history_limit=settings.history_limit,
    )


RunContext = Annotated[ResearchContext, Depends(research_context)]


def get_thread_registry(request: Request) -> ThreadRegistry:
    """The thread registry created at start-up (Lab 34)."""
    return request.app.state.thread_registry


Registry = Annotated[ThreadRegistry, Depends(get_thread_registry)]


@dataclass
class CheckedRequest:
    """A valid research request for a client that exists, ready for the graph."""

    body: ResearchRequest
    graph_input: dict
    thread_id: str  # what the analyst sees and sends back for a follow-up (Lab 31)
    thread_key: str  # what the checkpointer stores: "<username>:<thread_id>"


async def check_request(
    body: ResearchRequest, clients: Clients, user: CurrentUser
) -> CheckedRequest:
    client = await clients.get(body.client_id)
    if client is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Client {body.client_id} not found")
    profile = f"{client.name}, {client.segment}, risk profile {client.risk_profile}"
    graph_input = {
        "client_id": body.client_id,
        "client_profile": profile,
        "question": body.question,
    }
    thread_id = body.thread_id or uuid4().hex  # no thread given: a new conversation
    return CheckedRequest(
        body=body,
        graph_input=graph_input,
        thread_id=thread_id,
        thread_key=thread_key(user.username, thread_id),
    )


Checked = Annotated[CheckedRequest, Depends(check_request)]


async def mark_thread_used(
    checked: CheckedRequest, context: ResearchContext, registry: ThreadRegistry
) -> None:
    """Every run on a thread renews its expiry time (Lab 34)."""
    await registry.touch(
        checked.thread_key, context.analyst, checked.thread_id, checked.body.client_id
    )


def run_config(key: str) -> dict:
    """The configuration of one run on a thread: which thread, how many steps, which request."""
    return {
        **thread_config(key),
        "recursion_limit": get_settings().graph_recursion_limit,
        "metadata": {"request_id": get_request_id()},
    }


@router.post("", dependencies=[Depends(model_call_gate)])
async def submit_research(
    checked: Checked,
    graph: ResearchGraph,
    context: RunContext,
    cache: Cache,
    registry: Registry,
) -> ResearchResponse:
    client_id, question = checked.body.client_id, checked.body.question
    # A follow-up depends on its conversation, so only new questions use the cache
    use_cache = checked.body.thread_id is None
    result = await cache.get(client_id, question) if use_cache else None
    cached = result is not None
    if cached:
        logger.info("Research for %s answered from the cache", client_id)
    else:
        logger.info("Research started for %s", client_id)
        await mark_thread_used(checked, context, registry)
        # The output schema returns only answer, route and checked
        result = await graph.ainvoke(
            checked.graph_input, config=run_config(checked.thread_key), context=context
        )
        if use_cache:
            await cache.set(client_id, question, result)
        logger.info("Research finished for %s", client_id)
    return ResearchResponse(
        request_id=get_request_id(),
        client_id=client_id,
        status="completed",
        summary=result["answer"],
        route=result["route"],
        checked=result.get("checked"),
        thread_id=None if cached else checked.thread_id,  # a cached answer has no thread
        cached=cached,
        created_at=datetime.now(UTC),
    )


@router.post("/trace", dependencies=[Depends(model_call_gate)])
async def trace_research(
    checked: Checked, graph: ResearchGraph, context: RunContext, registry: Registry
) -> ResearchTrace:
    """The same research, answered together with its audit trail (never cached)."""
    client_id = checked.body.client_id
    logger.info("Traced research started for %s", client_id)
    await mark_thread_used(checked, context, registry)
    result = await graph.ainvoke(
        checked.graph_input,
        config=run_config(checked.thread_key),
        context=context,
        output_keys=TRACE_KEYS,
    )
    logger.info("Traced research finished for %s", client_id)
    return ResearchTrace(
        request_id=get_request_id(),
        client_id=client_id,
        summary=result["answer"],
        route=result["route"],
        checked=result.get("checked"),
        thread_id=checked.thread_id,
        trail=result["trail"],
        created_at=datetime.now(UTC),
    )


@router.post(
    "/stream", response_class=EventSourceResponse, dependencies=[Depends(model_call_gate)]
)
async def stream_research(
    checked: Checked, graph: ResearchGraph, context: RunContext, registry: Registry
) -> AsyncIterator[ServerSentEvent]:
    """The same research, streamed as Server-Sent Events while the model writes."""
    request_id = get_request_id()
    await mark_thread_used(checked, context, registry)
    yield ServerSentEvent(
        event="start",
        data={
            "request_id": request_id,
            "client_id": checked.body.client_id,
            "thread_id": checked.thread_id,
        },
    )
    try:
        async for mode, payload in graph.astream(
            checked.graph_input,
            config=run_config(checked.thread_key),
            context=context,
            stream_mode=["updates", "messages"],
        ):
            if mode == "messages":
                chunk, metadata = payload
                # Only the model's own words, and only from the answering stations
                if (
                    isinstance(chunk, AIMessageChunk)
                    and chunk.content
                    and metadata.get("langgraph_node") in ANSWER_NODES
                ):
                    yield ServerSentEvent(event="token", data=chunk.content)
            else:
                for node, update in payload.items():
                    yield ServerSentEvent(event="node", data={"node": node})
                    if node == "review" and update["status"] == "revising":
                        # The draft streamed so far was sent back: a corrected one follows
                        yield ServerSentEvent(
                            event="revision", data={"revision": update["revisions"]}
                        )
    except MODEL_ERRORS as error:
        logger.error("AI model not available during stream: %r", error)
        yield ServerSentEvent(event="error", data={"error": "model_unavailable"})
        return
    yield ServerSentEvent(event="done", data={"request_id": request_id})
