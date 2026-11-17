"""What the API shows about a conversation thread (Labs 31-37)."""

from pydantic import BaseModel, Field


class ThreadSnapshot(BaseModel):
    """The latest saved state of one thread, in a few plain fields."""

    thread_id: str
    client_id: str
    turns: int  # questions asked in this thread
    messages: int  # messages stored: prompt, questions, tool results, answers
    last_question: str
    last_answer: str | None = None
    route: str | None = None
    checkpoint_id: str
    step: int
    updated_at: str
    next: list[str] = []  # stations still to run: not empty after an interrupted run (Lab 35)


class ThreadMessage(BaseModel):
    """One message of a conversation, as the analyst would read it (Lab 32)."""

    type: str  # human, ai or tool
    content: str


class CheckpointSummary(BaseModel):
    """One saved checkpoint of a thread: one page of its history (Lab 36)."""

    checkpoint_id: str
    parent_checkpoint_id: str | None = None  # the checkpoint this one was made from
    step: int  # -1 = the input, 0 = the start, then one per finished step
    source: str  # input, loop, update or fork
    next: list[str]  # stations due after this checkpoint; empty = end of a run
    messages: int
    answer: str | None = None
    created_at: str


class RewindRequest(BaseModel):
    """Which checkpoint to go back to: one of the IDs from the history."""

    checkpoint_id: str = Field(min_length=1, max_length=64)


class CorrectionRequest(BaseModel):
    """A corrected question for the checkpoint right after intake (Lab 37)."""

    checkpoint_id: str = Field(min_length=1, max_length=64)
    question: str = Field(min_length=10, max_length=2000)
