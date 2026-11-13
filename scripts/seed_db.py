"""Lab 12: create the tables and load the sample clients (safe to run again)."""

import asyncio
import csv
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker

from sovereign_brain.core.settings import get_settings
from sovereign_brain.db.base import Base
from sovereign_brain.db.models import Client
from sovereign_brain.db.session import create_engine

SEED_FILE = Path("data/seed/clients.csv")


async def main() -> None:
    engine = create_engine(get_settings())
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    with SEED_FILE.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    async with async_sessionmaker(engine)() as session:
        for row in rows:
            await session.merge(Client(**row))
        await session.commit()
    await engine.dispose()
    print(f"Tables ready; {len(rows)} clients loaded from {SEED_FILE.as_posix()}")


if __name__ == "__main__":
    # psycopg's async mode needs the "selector" event loop on Windows
    loop_factory = asyncio.SelectorEventLoop if sys.platform == "win32" else None
    asyncio.run(main(), loop_factory=loop_factory)
