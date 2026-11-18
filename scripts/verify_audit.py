"""Lab 77: check the whole audit chain straight from the database (no API needed).

Usage: uv run python scripts/verify_audit.py
"""

import asyncio
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from sovereign_brain.core.settings import get_settings
from sovereign_brain.db.models import AuditEvent
from sovereign_brain.db.session import create_engine
from sovereign_brain.security.audit_chain import verify_chain


async def main() -> None:
    engine = create_engine(get_settings())
    async with async_sessionmaker(engine)() as session:
        chain = list(await session.scalars(select(AuditEvent).order_by(AuditEvent.seq)))
    await engine.dispose()
    problems = verify_chain(chain)
    print(f"{len(chain)} audit entries checked")
    for problem in problems:
        print(f"  PROBLEM  {problem}")
    print("INTACT" if not problems else "TAMPERED")


if __name__ == "__main__":
    # psycopg's async mode needs the "selector" event loop on Windows
    loop_factory = asyncio.SelectorEventLoop if sys.platform == "win32" else None
    asyncio.run(main(), loop_factory=loop_factory)
