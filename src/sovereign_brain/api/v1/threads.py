"""Conversation threads: look at what the Research Desk remembers (Labs 31-40)."""

import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status

from sovereign_brain.api.v1.research import (
    Archivist,
    Registry,
    ResearchGraph,
    RunContext,
    run_config,
)
from sovereign_brain.core.rate_limit import model_call_gate
from sovereign_brain.core.request_id import get_request_id
from sovereign_brain.core.security import CurrentUser, get_current_user
from sovereign_brain.memory.corrections import CORRECTABLE_NEXT, correct_question
from sovereign_brain.memory.threads import THREAD_ID_PATTERN, thread_config, thread_key
from sovereign_brain.schemas.memory import ArchiveResult
from sovereign_brain.schemas.research import ResearchResponse
from sovereign_brain.schemas.thread import (
    CheckpointSummary,
    CorrectionRequest,
    RewindRequest,
    ThreadMessage,
    ThreadSnapshot,
)

router = APIRouter(prefix="/v1/threads", tags=["threads"], dependencies=[Depends(get_current_user)])
logger = logging.getLogger("sovereign_brain.research")

ThreadId = Annotated[str, Path(pattern=THREAD_ID_PATTERN)]


@router.get("/{thread_id}")
async def read_thread(
    thread_id: ThreadId, graph: ResearchGraph, user: CurrentUser
) -> ThreadSnapshot:
    """The latest checkpoint of one of your threads."""
    snapshot = await graph.aget_state(thread_config(thread_key(user.username, thread_id)))
    if not snapshot.values:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Thread {thread_id} not found")
    values = snapshot.values
    questions = [m for m in values["messages"] if m.type == "human" and m.name != "reviewer"]
    return ThreadSnapshot(
        thread_id=thread_id,
        client_id=values["client_id"],
        turns=len(questions),
        messages=len(values["messages"]),
        last_question=values["question"],
        last_answer=values.get("answer"),
        route=values.get("route"),
        checkpoint_id=snapshot.config["configurable"]["checkpoint_id"],
        step=snapshot.metadata["step"],
        updated_at=snapshot.created_at,
        next=list(snapshot.next),
    )


@router.get("/{thread_id}/messages")
async def read_thread_messages(
    thread_id: ThreadId, graph: ResearchGraph, user: CurrentUser
) -> list[ThreadMessage]:
    """The conversation of one of your threads, read back from the checkpointer (Lab 32)."""
    snapshot = await graph.aget_state(thread_config(thread_key(user.username, thread_id)))
    if not snapshot.values:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Thread {thread_id} not found")
    return [
        ThreadMessage(type=m.type, content=str(m.content))
        for m in snapshot.values["messages"]
        if m.type != "system" and (m.content or m.type != "ai")  # no prompt, no empty tool requests
    ]


@router.post("/{thread_id}/resume", dependencies=[Depends(model_call_gate)])
async def resume_thread(
    thread_id: ThreadId,
    graph: ResearchGraph,
    user: CurrentUser,
    context: RunContext,
    registry: Registry,
) -> ResearchResponse:
    """Finish an interrupted run from its last checkpoint, without repeating finished stations."""
    key = thread_key(user.username, thread_id)
    config = run_config(key)
    snapshot = await graph.aget_state(config)
    if not snapshot.values:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Thread {thread_id} not found")
    if not snapshot.next:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Thread {thread_id} has no interrupted run to resume"
        )
    client_id = snapshot.values["client_id"]
    logger.info("Resuming thread %s at %s", thread_id, ", ".join(snapshot.next))
    await registry.touch(key, user.username, thread_id, client_id)
    # No input: LangGraph continues from the saved checkpoint instead of starting again
    result = await graph.ainvoke(None, config=config, context=context)
    return ResearchResponse(
        request_id=get_request_id(),
        client_id=client_id,
        status="completed",
        summary=result["answer"],
        route=result["route"],
        checked=result.get("checked"),
        thread_id=thread_id,
        created_at=datetime.now(UTC),
    )


@router.get("/{thread_id}/history")
async def read_thread_history(
    thread_id: ThreadId,
    graph: ResearchGraph,
    user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[CheckpointSummary]:
    """Every saved checkpoint of one of your threads, newest first (Lab 36)."""
    config = thread_config(thread_key(user.username, thread_id))
    history = [
        CheckpointSummary(
            checkpoint_id=snapshot.config["configurable"]["checkpoint_id"],
            parent_checkpoint_id=(
                snapshot.parent_config["configurable"]["checkpoint_id"]
                if snapshot.parent_config
                else None
            ),
            step=snapshot.metadata["step"],
            source=snapshot.metadata["source"],
            next=list(snapshot.next),
            messages=len(snapshot.values.get("messages", [])),
            answer=snapshot.values.get("answer"),
            created_at=snapshot.created_at,
        )
        async for snapshot in graph.aget_state_history(config, limit=limit)
    ]
    if not history:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Thread {thread_id} not found")
    return history


@router.post("/{thread_id}/rewind", dependencies=[Depends(model_call_gate)])
async def rewind_thread(
    thread_id: ThreadId,
    body: RewindRequest,
    graph: ResearchGraph,
    user: CurrentUser,
    context: RunContext,
    registry: Registry,
) -> ResearchResponse:
    """Go back to an earlier checkpoint and run again from there (Lab 36).

    The stations after that checkpoint run again; the new run becomes the thread's latest
    state, and the old checkpoints stay in the history.
    """
    key = thread_key(user.username, thread_id)
    config = run_config(key)
    config["configurable"]["checkpoint_id"] = body.checkpoint_id
    snapshot = await graph.aget_state(config)
    if not snapshot.values:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"Checkpoint {body.checkpoint_id} not found in thread {thread_id}",
        )
    if not snapshot.next:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Checkpoint {body.checkpoint_id} is the end of a run; nothing to run again",
        )
    client_id = snapshot.values["client_id"]
    logger.info("Rewinding thread %s to step %s", thread_id, snapshot.metadata["step"])
    await registry.touch(key, user.username, thread_id, client_id)
    # No input + a checkpoint_id: LangGraph starts a new branch from that checkpoint
    result = await graph.ainvoke(None, config=config, context=context)
    return ResearchResponse(
        request_id=get_request_id(),
        client_id=client_id,
        status="completed",
        summary=result["answer"],
        route=result["route"],
        checked=result.get("checked"),
        thread_id=thread_id,
        created_at=datetime.now(UTC),
    )


@router.post("/{thread_id}/correct", dependencies=[Depends(model_call_gate)])
async def correct_thread(
    thread_id: ThreadId,
    body: CorrectionRequest,
    graph: ResearchGraph,
    user: CurrentUser,
    context: RunContext,
    registry: Registry,
) -> ResearchResponse:
    """Correct the question at an earlier checkpoint and run a new branch from there (Lab 37).

    Only the checkpoint right after intake can be corrected: there the question has been
    read and nothing has been decided yet.
    """
    key = thread_key(user.username, thread_id)
    config = run_config(key)
    config["configurable"]["checkpoint_id"] = body.checkpoint_id
    snapshot = await graph.aget_state(config)
    if not snapshot.values:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"Checkpoint {body.checkpoint_id} not found in thread {thread_id}",
        )
    if snapshot.next != CORRECTABLE_NEXT:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Checkpoint {body.checkpoint_id} is not right after intake; "
            "choose the checkpoint whose next station is recall",
        )
    client_id = snapshot.values["client_id"]
    logger.info("Correcting thread %s at step %s", thread_id, snapshot.metadata["step"])
    await registry.touch(key, user.username, thread_id, client_id)
    corrected = await correct_question(graph, snapshot, body.question, user.username)
    # Run from the corrected checkpoint: every station after intake runs again
    config["configurable"]["checkpoint_id"] = corrected["configurable"]["checkpoint_id"]
    result = await graph.ainvoke(None, config=config, context=context)
    return ResearchResponse(
        request_id=get_request_id(),
        client_id=client_id,
        status="completed",
        summary=result["answer"],
        route=result["route"],
        checked=result.get("checked"),
        thread_id=thread_id,
        created_at=datetime.now(UTC),
    )


@router.delete("/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_thread(
    thread_id: ThreadId, graph: ResearchGraph, user: CurrentUser, registry: Registry
) -> Response:
    """Erase one of your threads now: every checkpoint and its record (Lab 34)."""
    key = thread_key(user.username, thread_id)
    snapshot = await graph.aget_state(thread_config(key))
    if not snapshot.values:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Thread {thread_id} not found")
    await graph.checkpointer.adelete_thread(key)
    await registry.forget(key)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{thread_id}/archive", dependencies=[Depends(model_call_gate)])
async def archive_thread(
    thread_id: ThreadId,
    graph: ResearchGraph,
    user: CurrentUser,
    registry: Registry,
    archivist: Archivist,
) -> ArchiveResult:
    """Summarise one of your threads into semantic memory, then erase it (Lab 40)."""
    if archivist is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Semantic memory is switched off")
    key = thread_key(user.username, thread_id)
    summary = await archivist.archive(graph, key)
    if summary is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Thread {thread_id} not found")
    await graph.checkpointer.adelete_thread(key)
    await registry.forget(key)
    return ArchiveResult(thread_id=thread_id, summary=summary)
