"""A Redis cache for research answers: the same question for the same client is answered once."""

import hashlib
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
        """The same client and question (ignoring case and extra spaces) give the same key."""
        text = f"{client_id}|{' '.join(question.lower().split())}"
        return "research:v1:" + hashlib.sha256(text.encode("utf-8")).hexdigest()

    async def get(self, client_id: str, question: str) -> str | None:
        try:
            return await self.client.get(self.key(client_id, question))
        except RedisError as error:
            logger.warning("Cache not available, answering without it: %r", error)
            return None

    async def set(self, client_id: str, question: str, summary: str) -> None:
        try:
            await self.client.set(self.key(client_id, question), summary, ex=self.ttl_seconds)
        except RedisError as error:
            logger.warning("Cache not available, answer not stored: %r", error)


def get_cache(request: Request) -> ResearchCache:
    return request.app.state.cache


Cache = Annotated[ResearchCache, Depends(get_cache)]
