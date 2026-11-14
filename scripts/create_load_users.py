"""Lab 20: create (or disable) the accounts that the load test signs in with.

The password is read from the environment variable SB_LOAD_TEST_PASSWORD, the same one
that locustfile.py uses. Local load tests only: never create these accounts in production.
"""

import argparse
import asyncio
import os
import sys

from sqlalchemy.ext.asyncio import async_sessionmaker

from sovereign_brain.core.security import hash_password
from sovereign_brain.core.settings import get_settings
from sovereign_brain.db.base import Base
from sovereign_brain.db.models import User
from sovereign_brain.db.session import create_engine


async def main(count: int, disable: bool) -> None:
    password = os.environ.get("SB_LOAD_TEST_PASSWORD", "")
    if len(password) < 12:
        sys.exit("Set SB_LOAD_TEST_PASSWORD to a password of at least 12 characters first.")
    hashed = hash_password(password)  # one hash for every load-test account

    engine = create_engine(get_settings())
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine)() as session:
        for number in range(1, count + 1):
            user = User(
                username=f"load-{number:02d}",
                full_name=f"Load Test User {number:02d}",
                hashed_password=hashed,
                role="analyst",
                disabled=disable,
            )
            await session.merge(user)
        await session.commit()
    await engine.dispose()
    state = "disabled" if disable else "ready"
    print(f"Load-test users load-01 ... load-{count:02d} {state}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create or disable load-test users.")
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument("--disable", action="store_true", help="switch the accounts off")
    args = parser.parse_args()
    # psycopg's async mode needs the "selector" event loop on Windows
    loop_factory = asyncio.SelectorEventLoop if sys.platform == "win32" else None
    asyncio.run(main(args.count, args.disable), loop_factory=loop_factory)
