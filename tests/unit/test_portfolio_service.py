from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from sovereign_brain.services.portfolio import PortfolioService


async def exposure(database_url: str, client_id: str, sector: str) -> dict:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        return await PortfolioService(async_sessionmaker(engine)).sector_exposure(client_id, sector)
    finally:
        await engine.dispose()


async def test_sector_exposure_is_computed_from_the_positions(database_url: str) -> None:
    result = await exposure(database_url, "c-1042", " energy ")

    assert result == {
        "client_id": "C-1042",
        "sector": "energy",
        "sector_value_usd": 185000,
        "portfolio_value_usd": 1000000,
        "percent": 18.5,
    }


async def test_a_client_without_positions_gets_a_clear_message(database_url: str) -> None:
    result = await exposure(database_url, "C-2077", "Energy")

    assert result == {"client_id": "C-2077", "error": "no positions found"}
