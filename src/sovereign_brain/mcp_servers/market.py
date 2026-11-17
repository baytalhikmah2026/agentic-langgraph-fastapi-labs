"""The market-data MCP server (Lab 46): a secure gateway between the agent and the market API.

The bearer token is added here, by code. The model never sees it and cannot change it.
Every answer from the API is checked with a strict Pydantic model before the agent may read
it: unknown fields, a price of 0, a currency other than US dollars or a malformed ticker are
refused. That protects the agent from poisoned or broken data.

Run it on its own with: uv run python -m sovereign_brain.mcp_servers.market
"""

import os
from datetime import date
from typing import Annotated, Literal

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, ValidationError

API_URL = os.environ.get("SB_MARKET_API_URL", "http://localhost:8100")
API_TOKEN = os.environ.get("SB_MARKET_API_TOKEN", "")


class MarketQuote(BaseModel):
    """What a valid answer from the market API must look like, and nothing more."""

    model_config = ConfigDict(extra="forbid")  # an extra field could smuggle in instructions

    ticker: str = Field(pattern=r"^[A-Z0-9]{1,6}$")
    name: str = Field(min_length=1, max_length=80)
    price: float = Field(gt=0, lt=1_000_000)
    currency: Literal["USD"]
    as_of: date


def create_server(
    api_url: str, token: str, transport: httpx.AsyncBaseTransport | None = None
) -> FastMCP:
    """A market-data server for one API (tests pass a transport that reaches a test API)."""
    server = FastMCP(
        "market-data",
        instructions="Latest internal prices of the stocks and bonds that the bank's clients hold.",
    )

    @server.tool()
    async def get_quote(
        ticker: Annotated[
            str, Field(pattern=r"^[A-Za-z0-9]{1,6}$", description="A ticker, for example GLFP")
        ],
    ) -> MarketQuote:
        """The latest internal price of one stock or bond, in US dollars."""
        async with httpx.AsyncClient(
            base_url=api_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=5.0,
            transport=transport,
        ) as client:
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

    return server


server = create_server(API_URL, API_TOKEN)

if __name__ == "__main__":
    server.run()
