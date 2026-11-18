"""The right to erasure (Lab 78): remove what the desk keeps about one client, everywhere.

GDPR lets a person ask a company to erase their personal data. The desk's working data about
a client lives in three stores: conversations (checkpoints in PostgreSQL), long-term memories
(Qdrant) and cached answers (Redis). Records the bank must keep by law (approvals, signatures,
the audit log) are not erased; the retention policy says so, and why.
"""

from langgraph.graph.state import CompiledStateGraph

from sovereign_brain.core.cache import ResearchCache
from sovereign_brain.core.settings import Settings
from sovereign_brain.memory.retention import ThreadRegistry
from sovereign_brain.memory.semantic import SemanticMemory


async def erase_client(
    client_id: str,
    registry: ThreadRegistry,
    graph: CompiledStateGraph,
    memory: SemanticMemory | None,
    cache: ResearchCache,
) -> dict[str, int]:
    """Erase one client's working data; returns how much was removed from each store."""
    keys = await registry.keys_for_client(client_id)
    for key in keys:
        await graph.checkpointer.adelete_thread(key)  # the conversation itself
        await registry.forget(key)  # and the registry row about it
    memories = await memory.forget_client(client_id) if memory is not None else 0
    cached = await cache.forget_client(client_id)
    return {"threads": len(keys), "memories": memories, "cached_answers": cached}


def retention_policy(settings: Settings) -> list[dict[str, str]]:
    """What the desk keeps, for how long, and what happens on an erasure request."""
    return [
        {
            "data": "Research conversations (PostgreSQL checkpoints)",
            "kept_for": f"{settings.thread_ttl_minutes // 1440} days after last use",
            "on_erasure": "deleted at once",
        },
        {
            "data": "Long-term memories (Qdrant)",
            "kept_for": "until erased",
            "on_erasure": "deleted at once",
        },
        {
            "data": "Cached answers (Redis)",
            "kept_for": f"{settings.cache_ttl_seconds // 60} minutes",
            "on_erasure": "deleted at once",
        },
        {
            "data": "Shared team cases (Redis)",
            "kept_for": f"{settings.case_ttl_minutes // 60} hours",
            "on_erasure": "expire on their own",
        },
        {
            "data": "Approvals, signatures and the audit log (PostgreSQL)",
            "kept_for": "10 years",
            "on_erasure": "kept: legal obligation (GDPR Art. 17(3)(b)); the erasure is logged",
        },
    ]
