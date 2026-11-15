"""Labs 12 and 22: create the tables, load sample clients and positions (safe to rerun)."""

import asyncio
import csv
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker

from sovereign_brain.core.settings import get_settings
from sovereign_brain.db.base import Base
from sovereign_brain.db.models import Client, Position
from sovereign_brain.db.session import create_engine

SEED_FILE = Path("data/seed/clients.csv")
POSITIONS_FILE = Path("data/seed/positions.csv")


async def main() -> None:
    engine = create_engine(get_settings())
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    with SEED_FILE.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    with POSITIONS_FILE.open(encoding="utf-8", newline="") as file:
        positions = list(csv.DictReader(file))
    async with async_sessionmaker(engine)() as session:
        for row in rows:
            await session.merge(Client(**row))
        await session.flush()  # clients first: every position points to a client
        for row in positions:
            row["id"] = int(row["id"])
            row["market_value_usd"] = int(row["market_value_usd"])
            await session.merge(Position(**row))
        await session.commit()
    await engine.dispose()
    print(f"Tables ready; {len(rows)} clients and {len(positions)} positions loaded")


if __name__ == "__main__":
    # psycopg's async mode needs the "selector" event loop on Windows
    loop_factory = asyncio.SelectorEventLoop if sys.platform == "win32" else None
    asyncio.run(main(), loop_factory=loop_factory)
