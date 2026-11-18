"""Database engine and one session per request."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from fastapi.requests import HTTPConnection
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from sovereign_brain.core.settings import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(settings.database_url, pool_pre_ping=True)


async def get_session(connection: HTTPConnection) -> AsyncIterator[AsyncSession]:
    """Open a session for this request and close it when the response is done.

    Lab 98: HTTPConnection covers both HTTP requests and WebSockets.
    """
    async with connection.app.state.session_factory() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(get_session)]
