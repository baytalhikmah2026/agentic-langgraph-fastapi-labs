"""The desk-reference MCP server (Lab 44): risk limits and a small finance glossary.

It runs as its own process and speaks the Model Context Protocol over stdio (its standard
input and output). Any MCP client can discover and call its tools: our API, an IDE, a chat app.

Run it on its own with: uv run python -m sovereign_brain.mcp_servers.desk
"""

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from sovereign_brain.services.risk import LOSS_LIMITS, RiskProfile

GLOSSARY = {
    "bond": "A loan to a company or government that pays interest and is repaid on a set date.",
    "concentration risk": "The danger of a large loss because much of a portfolio sits in one "
    "company, sector or country.",
    "drawdown": "The fall from a portfolio's highest value to its lowest point before it recovers.",
    "equity": "A share in the ownership of a company, also called a stock.",
    "exposure": "How much of a portfolio is affected by one market, sector or risk, in percent.",
    "stress test": "A what-if calculation of the loss a portfolio would suffer if prices fell.",
}

server = FastMCP(
    "desk-reference",
    instructions="Reference data of the Crescent Ledger Bank Research Desk: "
    "the risk limit of each risk profile, and a glossary of finance terms.",
)


class RiskLimit(BaseModel):
    """A risk profile and the largest loss from one sector shock it accepts."""

    risk_profile: RiskProfile
    max_loss_percent: float


@server.tool()
def risk_limit(
    risk_profile: Annotated[
        RiskProfile, Field(description="conservative, moderate, growth or aggressive")
    ],
) -> RiskLimit:
    """The largest loss from one sector shock that a risk profile accepts, in % of the portfolio."""
    return RiskLimit(risk_profile=risk_profile, max_loss_percent=LOSS_LIMITS[risk_profile])


@server.tool()
def glossary(
    term: Annotated[
        str, Field(min_length=2, max_length=40, description="A finance term, e.g. exposure")
    ],
) -> str:
    """A plain-words definition of a finance term used on the Research Desk."""
    key = term.strip().lower()
    if key not in GLOSSARY:
        raise ValueError(f"Unknown term '{term}'. Known terms: {', '.join(sorted(GLOSSARY))}")
    return GLOSSARY[key]


if __name__ == "__main__":
    server.run()  # stdio: the client starts this process and talks through its input and output
