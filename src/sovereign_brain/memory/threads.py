"""Conversation threads (Lab 31): one thread = one conversation, remembered between requests.

Analysts choose short thread IDs such as "energy-review". The checkpointer stores each
thread under "<username>:<thread_id>", so two analysts can both use "energy-review"
without ever seeing each other's conversation.
"""

THREAD_ID_PATTERN = r"^[A-Za-z0-9-]{1,64}$"


def thread_key(username: str, thread_id: str) -> str:
    """The key the checkpointer stores a thread under: always tied to its owner."""
    return f"{username}:{thread_id}"


def thread_config(key: str) -> dict:
    """The run configuration that selects a thread."""
    return {"configurable": {"thread_id": key}}
