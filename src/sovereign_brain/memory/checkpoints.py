"""Where conversation threads are kept (Lab 32): the card file of the Research Desk.

SB_CHECKPOINT_STORE chooses it:
- "memory": in the API process (Lab 31); fast, lost on every restart; used by the tests.
- "sqlite": in one SQLite file (SB_CHECKPOINT_SQLITE_PATH); survives restarts.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from sovereign_brain.core.settings import Settings

logger = logging.getLogger("sovereign_brain.memory")


@asynccontextmanager
async def open_checkpointer(settings: Settings) -> AsyncIterator[BaseCheckpointSaver]:
    """Open the chosen checkpointer for the lifetime of the API, and close it afterwards."""
    if settings.checkpoint_store == "sqlite":
        path = Path(settings.checkpoint_sqlite_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        async with AsyncSqliteSaver.from_conn_string(str(path)) as saver:
            await saver.setup()  # creates the tables on first use
            logger.info("Thread memory: SQLite file %s", path)
            yield saver
    else:
        logger.info("Thread memory: in the API process (lost on restart)")
        yield InMemorySaver()
