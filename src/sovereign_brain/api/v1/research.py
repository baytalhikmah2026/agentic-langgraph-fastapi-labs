"""Research requests: the main counter of the Research Desk."""

import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.sse import EventSourceResponse, ServerSentEvent
from langchain_core.messages import AIMessageChunk
from langgraph.graph.state import CompiledStateGraph

from sovereign_brain.core.cache import Cache
from sovereign_brain.core.errors import MODEL_ERRORS
from sovereign_brain.core.rate_limit import model_call_gate
from sovereign_brain.core.request_id import get_request_id
from sovereign_brain.core.security import get_current_user
from sovereign_brain.core.settings import get_settings
from sovereign_brain.db.repository import Clients
from sovereign_brain.schemas.research import ResearchRequest, ResearchResponse

router = APIRouter(
    prefix="/v1/research", tags=["research"], dependencies=[Depends(get_current_user)]
)
logger = logging.getLogger("sovereign_brain.research")


def get_research_graph(request: Request) -> CompiledStateGraph:
    """The graph built once at start-up (see lifespan in main.py)."""
    return request.app.state.research_graph


ResearchGraph = Annotated[CompiledStateGraph, Depends(get_research_graph)]


@dataclass
class CheckedRequest:
    """A valid research request for a client that exists, ready for the graph."""

    body: ResearchRequest
    graph_input: dict


async def check_request(body: ResearchRequest, clients: Clients) -> CheckedRequest:
    client = await clients.get(body.client_id)
    if client is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Client {body.client_id} not found")
    profile = f"{client.name}, {client.segment}, risk profile {client.risk_profile}"
    graph_input = {
        "client_id": body.client_id,
        "client_profile": profile,
        "question": body.question,
    }
    return CheckedRequest(body=body, graph_input=graph_input)


Checked = Annotated[CheckedRequest, Depends(check_request)]


def run_config() -> dict:
    return {
        "recursion_limit": get_settings().graph_recursion_limit,
        "metadata": {"request_id": get_request_id()},
    }


@router.post("", dependencies=[Depends(model_call_gate)])
async def submit_research(
    checked: Checked, graph: ResearchGraph, cache: Cache
) -> ResearchResponse:
    client_id, question = checked.body.client_id, checked.body.question
    result = await cache.get(client_id, question)
    cached = result is not None
    if cached:
        logger.info("Research for %s answered from the cache", client_id)
    else:
        logger.info("Research started for %s", client_id)
        # The output schema returns only answer, route and checked
        result = await graph.ainvoke(checked.graph_input, config=run_config())
        await cache.set(client_id, question, result)
        logger.info("Research finished for %s", client_id)
    return ResearchResponse(
        request_id=get_request_id(),
        client_id=client_id,
        status="completed",
        summary=result["answer"],
        route=result["route"],
        checked=result.get("checked"),
        cached=cached,
        created_at=datetime.now(UTC),
    )


@router.post(
    "/stream", response_class=EventSourceResponse, dependencies=[Depends(model_call_gate)]
)
async def stream_research(
    checked: Checked, graph: ResearchGraph
) -> AsyncIterator[ServerSentEvent]:
    """The same research, streamed as Server-Sent Events while the model writes."""
    request_id = get_request_id()
    yield ServerSentEvent(
        event="start", data={"request_id": request_id, "client_id": checked.body.client_id}
    )
    try:
        async for mode, payload in graph.astream(
            checked.graph_input, config=run_config(), stream_mode=["updates", "messages"]
        ):
            if mode == "messages":
                chunk, _metadata = payload
                # Only the model's own words: nodes also return prompts and tool results
                if isinstance(chunk, AIMessageChunk) and chunk.content:
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
