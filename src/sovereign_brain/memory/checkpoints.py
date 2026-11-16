"""Where conversation threads are kept (Labs 32-33): the card file of the Research Desk.

SB_CHECKPOINT_STORE chooses it:
- "memory": in the API process (Lab 31); fast, lost on every restart; used by the tests.
- "sqlite": in one SQLite file (SB_CHECKPOINT_SQLITE_PATH); survives restarts.
- "postgres": in the project's PostgreSQL database (Lab 33); survives rebuilds, shared by
  every API copy, reached through a pool of connections.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from sqlalchemy.engine import make_url

from sovereign_brain.core.settings import Settings

logger = logging.getLogger("sovereign_brain.memory")


def postgres_conninfo(database_url: str) -> str:
    """SQLAlchemy's "postgresql+psycopg://..." as the plain "postgresql://..." psycopg reads."""
    url = make_url(database_url).set(drivername="postgresql")
    return url.render_as_string(hide_password=False)


@asynccontextmanager
async def open_checkpointer(settings: Settings) -> AsyncIterator[BaseCheckpointSaver]:
    """Open the chosen checkpointer for the lifetime of the API, and close it afterwards."""
    if settings.checkpoint_store == "postgres":
        async with AsyncConnectionPool(
            postgres_conninfo(settings.database_url),
            min_size=1,
            max_size=settings.checkpoint_pool_size,
            # What the Postgres checkpointer needs from every connection it borrows
            kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
            open=False,  # opened by "async with", closed when the block ends
        ) as pool:
            saver = AsyncPostgresSaver(pool)
            await saver.setup()  # creates or upgrades the checkpoint tables
            logger.info("Thread memory: PostgreSQL (up to %d connections)", pool.max_size)
            yield saver
    elif settings.checkpoint_store == "sqlite":
        path = Path(settings.checkpoint_sqlite_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        async with AsyncSqliteSaver.from_conn_string(str(path)) as saver:
            await saver.setup()  # creates the tables on first use
            logger.info("Thread memory: SQLite file %s", path)
            yield saver
    else:
        logger.info("Thread memory: in the API process (lost on restart)")
        yield InMemorySaver()
