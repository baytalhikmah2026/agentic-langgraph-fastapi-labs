"""Lab 16: create or update a Research Desk user (asks for the password, never shows it)."""

import argparse
import asyncio
import getpass
import sys

from sqlalchemy.ext.asyncio import async_sessionmaker

from sovereign_brain.core.security import hash_password
from sovereign_brain.core.settings import get_settings
from sovereign_brain.db.base import Base
from sovereign_brain.db.models import User
from sovereign_brain.db.session import create_engine


async def main(username: str, full_name: str, role: str) -> None:
    password = getpass.getpass(f"New password for {username}: ")
    if len(password) < 12:
        sys.exit("The password must have at least 12 characters.")

    engine = create_engine(get_settings())
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine)() as session:
        user = User(
            username=username,
            full_name=full_name,
            hashed_password=hash_password(password),
            role=role,
            disabled=False,
        )
        await session.merge(user)
        await session.commit()
    await engine.dispose()
    print(f"User {username} ({role}) saved.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create or update a user.")
    parser.add_argument("username")
    parser.add_argument("--full-name", required=True)
    parser.add_argument("--role", default="analyst")
    args = parser.parse_args()
    # psycopg's async mode needs the "selector" event loop on Windows
    loop_factory = asyncio.SelectorEventLoop if sys.platform == "win32" else None
    asyncio.run(main(args.username, args.full_name, args.role), loop_factory=loop_factory)
