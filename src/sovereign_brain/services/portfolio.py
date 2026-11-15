"""Client portfolios: the facts the agents may quote (Lab 22)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sovereign_brain.db.models import Position


class PortfolioService:
    """Reads positions from the database; every method opens its own short session."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self.sessions = sessions

    async def positions(self, client_id: str) -> dict:
        client_id = client_id.strip().upper()
        query = (
            select(Position)
            .where(Position.client_id == client_id)
            .order_by(Position.market_value_usd.desc())
        )
        async with self.sessions() as session:
            rows = (await session.scalars(query)).all()
        holdings = [
            {
                "ticker": p.ticker,
                "name": p.name,
                "sector": p.sector,
                "market_value_usd": p.market_value_usd,
            }
            for p in rows
        ]
        return {"client_id": client_id, "positions": holdings}

    async def sector_exposure(self, client_id: str, sector: str) -> dict:
        portfolio = await self.positions(client_id)
        holdings = portfolio["positions"]
        if not holdings:
            return {"client_id": portfolio["client_id"], "error": "no positions found"}
        total = sum(h["market_value_usd"] for h in holdings)
        wanted = sector.strip().lower()
        in_sector = sum(h["market_value_usd"] for h in holdings if h["sector"].lower() == wanted)
        return {
            "client_id": portfolio["client_id"],
            "sector": sector.strip(),
            "sector_value_usd": in_sector,
            "portfolio_value_usd": total,
            "percent": round(100 * in_sector / total, 1),
        }
