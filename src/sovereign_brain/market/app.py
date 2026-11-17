"""Crescent Ledger Bank's internal market-data API (Lab 46): a stand-in for a real bank system.

It runs as its own service (Compose service `market`) and answers only callers that present
the shared bearer token. In a real bank, another team would own a system like this.

Run it on its own with: uv run fastapi dev src/sovereign_brain/market/app.py --port 8100
"""

import csv
import secrets
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from sovereign_brain.core.settings import get_settings

PRICES_FILE = Path("data/seed/prices.csv")
bearer = HTTPBearer(auto_error=False)  # we answer a missing token ourselves


class Quote(BaseModel):
    """The latest price of one stock or bond."""

    ticker: str
    name: str
    price: float
    currency: str
    as_of: date


@lru_cache
def load_quotes() -> dict[str, Quote]:
    """All prices from the seed file, by ticker (read once)."""
    with PRICES_FILE.open(encoding="utf-8", newline="") as file:
        return {row["ticker"]: Quote.model_validate(row) for row in csv.DictReader(file)}


def check_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> None:
    """Only callers with the shared bearer token get an answer."""
    expected = get_settings().market_api_token.get_secret_value()
    if credentials is None or not secrets.compare_digest(credentials.credentials, expected):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Missing or wrong bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )


quotes = APIRouter(prefix="/v1/quotes", dependencies=[Depends(check_token)])


@quotes.get("/{ticker}")
async def get_quote(ticker: str) -> Quote:
    quote = load_quotes().get(ticker.upper())
    if quote is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No quote for {ticker}")
    return quote


app = FastAPI(title="Crescent Market Data (internal)")
app.include_router(quotes)


@app.get("/health")
async def health() -> dict:
    """For the Compose health check; no token needed and no data shown."""
    return {"status": "ok"}
