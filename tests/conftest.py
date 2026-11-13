"""Shared test setup (Labs 17 and 18). Lab 19 adds the full set of fixtures."""

import pytest

from sovereign_brain.core.cache import ResearchCache
from sovereign_brain.core.rate_limit import limiter


@pytest.fixture(autouse=True)
def reset_rate_limits() -> None:
    """Every test starts with empty rate-limit counters."""
    limiter.reset()


@pytest.fixture(autouse=True)
def in_memory_cache(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Tests never need Redis: the cache keeps its answers in a dictionary instead."""
    store: dict[str, str] = {}

    async def get(self: ResearchCache, client_id: str, question: str) -> str | None:
        return store.get(self.key(client_id, question))

    async def set(self: ResearchCache, client_id: str, question: str, summary: str) -> None:
        store[self.key(client_id, question)] = summary

    monkeypatch.setattr(ResearchCache, "get", get)
    monkeypatch.setattr(ResearchCache, "set", set)
    return store
