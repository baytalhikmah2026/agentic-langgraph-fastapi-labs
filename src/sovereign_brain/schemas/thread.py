"""What the API shows about a conversation thread (Lab 31)."""

from pydantic import BaseModel


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


class ThreadMessage(BaseModel):
    """One message of a conversation, as the analyst would read it (Lab 32)."""

    type: str  # human, ai or tool
    content: str
