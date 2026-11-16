"""Conversation threads: look at what the Research Desk remembers (Labs 31-34)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status

from sovereign_brain.api.v1.research import Registry, ResearchGraph
from sovereign_brain.core.security import CurrentUser, get_current_user
from sovereign_brain.memory.threads import THREAD_ID_PATTERN, thread_config, thread_key
from sovereign_brain.schemas.thread import ThreadMessage, ThreadSnapshot

router = APIRouter(prefix="/v1/threads", tags=["threads"], dependencies=[Depends(get_current_user)])

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
