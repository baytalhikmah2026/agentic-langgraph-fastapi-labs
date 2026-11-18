"""A Redis cache for research answers: the same question for the same client is answered once."""

import hashlib
import json
import logging
from typing import Annotated

from fastapi import Depends, Request
from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger("sovereign_brain.cache")


class ResearchCache:
    def __init__(self, client: Redis, ttl_seconds: int) -> None:
        self.client = client
        self.ttl_seconds = ttl_seconds

    @staticmethod
    def key(client_id: str, question: str) -> str:
        """The same client and question (ignoring case and extra spaces) give the same key.

        v2 (Lab 25): the cached value is the graph's whole output as JSON, not only the summary.
        """
        text = f"{client_id}|{' '.join(question.lower().split())}"
        return "research:v2:" + hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def client_index(client_id: str) -> str:
        """A set of every cached key about one client (Lab 78), so they can all be erased."""
        return f"research:v2:client:{client_id}"

    async def get(self, client_id: str, question: str) -> dict | None:
        try:
            value = await self.client.get(self.key(client_id, question))
        except RedisError as error:
            logger.warning("Cache not available, answering without it: %r", error)
            return None
        return json.loads(value) if value is not None else None

    async def set(self, client_id: str, question: str, result: dict) -> None:
        value = json.dumps(result)
        try:
            key = self.key(client_id, question)
            await self.client.set(key, value, ex=self.ttl_seconds)
            await self.client.sadd(self.client_index(client_id), key)  # Lab 78
            await self.client.expire(self.client_index(client_id), self.ttl_seconds)
        except RedisError as error:
            logger.warning("Cache not available, answer not stored: %r", error)

    async def forget_client(self, client_id: str) -> int:
        """Delete every cached answer about one client (Lab 78); returns how many.

        No "cache not available" fallback here: an erasure must not quietly half-succeed.
        """
        index = self.client_index(client_id)
        keys = await self.client.smembers(index)
        removed = await self.client.delete(*keys) if keys else 0
        await self.client.delete(index)
        return removed


def get_cache(request: Request) -> ResearchCache:
    return request.app.state.cache


Cache = Annotated[ResearchCache, Depends(get_cache)]
