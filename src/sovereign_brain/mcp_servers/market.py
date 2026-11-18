"""The market-data MCP server (Lab 46): a secure gateway between the agent and the market API.

The bearer token is added here, by code. The model never sees it and cannot change it.
Every answer from the API is checked with a strict Pydantic model before the agent may read
it: unknown fields, a price of 0, a currency other than US dollars or a malformed ticker are
refused. That protects the agent from poisoned or broken data.
Lab 48: get_quotes asks for several prices at the same time (asyncio.gather).
Lab 74: with SB_MARKET_CA_FILE set, the server talks to the API over mutual TLS.

Run it on its own with: uv run python -m sovereign_brain.mcp_servers.market
"""

import asyncio
import os
import ssl
from datetime import date
from typing import Annotated, Literal

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from sovereign_brain.security.certs import client_context

API_URL = os.environ.get("SB_MARKET_API_URL", "http://localhost:8100")
API_TOKEN = os.environ.get("SB_MARKET_API_TOKEN", "")
CA_FILE = os.environ.get("SB_MARKET_CA_FILE", "")

Ticker = Annotated[
    str, Field(pattern=r"^[A-Za-z0-9]{1,6}$", description="A ticker, for example GLFP")
]


class MarketQuote(BaseModel):
    """What a valid answer from the market API must look like, and nothing more."""

    model_config = ConfigDict(extra="forbid")  # an extra field could smuggle in instructions

    ticker: str = Field(pattern=r"^[A-Z0-9]{1,6}$")
    name: str = Field(min_length=1, max_length=80)
    price: float = Field(gt=0, lt=1_000_000)
    currency: Literal["USD"]
    as_of: date


async def fetch_quote(client: httpx.AsyncClient, ticker: str) -> MarketQuote:
    """One price from the API, checked against MarketQuote."""
    response = await client.get(f"/v1/quotes/{ticker.upper()}")
    if response.status_code == httpx.codes.NOT_FOUND:
        raise ValueError(f"No quote for {ticker.upper()}")
    response.raise_for_status()  # 401 and other errors become a tool error
    try:
        return MarketQuote.model_validate(response.json())
    except ValidationError as error:
        # Name the bad fields only: the bad values themselves must not reach the model
        fields = ", ".join(sorted({str(e["loc"][0]) for e in error.errors() if e["loc"]}))
        raise ValueError(f"The market API sent an invalid quote ({fields}); not used") from None


def create_server(
    api_url: str,
    token: str,
    transport: httpx.AsyncBaseTransport | None = None,
    tls: ssl.SSLContext | None = None,
) -> FastMCP:
    """A market-data server for one API (tests pass a transport that reaches a test API)."""
    server = FastMCP(
        "market-data",
        instructions="Latest internal prices of the stocks and bonds that the bank's clients hold.",
    )

    def api_client() -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=api_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=5.0,
            transport=transport,
            verify=tls if tls is not None else True,  # our CA and our certificate (Lab 74)
        )

    @server.tool()
    async def get_quote(ticker: Ticker) -> MarketQuote:
        """The latest internal price of one stock or bond, in US dollars."""
        async with api_client() as client:
            return await fetch_quote(client, ticker)

    @server.tool()
    async def get_quotes(
        tickers: Annotated[list[Ticker], Field(min_length=1, max_length=10)],
    ) -> list[MarketQuote]:
        """The latest internal prices of several stocks or bonds at once, in US dollars."""
        wanted = list(dict.fromkeys(t.upper() for t in tickers))  # each ticker once, in order
        async with api_client() as client:
            # All requests are sent together; the slowest one sets the total time
            return list(await asyncio.gather(*(fetch_quote(client, t) for t in wanted)))

    return server


tls = None
if CA_FILE:
    tls = client_context(
        CA_FILE, os.environ["SB_MARKET_CLIENT_CERT"], os.environ["SB_MARKET_CLIENT_KEY"]
    )
server = create_server(API_URL, API_TOKEN, tls=tls)

if __name__ == "__main__":
    server.run()
