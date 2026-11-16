"""Routing for the research graph: which track does a question take?

Lab 23: word rules (instant, always available).
Lab 30: the model decides with structured output; the rules remain the safety net.
"""

import re
from typing import Literal

from pydantic import BaseModel, Field

Route = Literal["general", "portfolio"]

ROUTER_PROMPT = (
    "You route questions on the Research Desk of Crescent Ledger Bank. "
    "Choose 'portfolio' when the question is about the client's own holdings, positions, "
    "sectors, exposure or allocation. Choose 'general' for everything else, such as "
    "definitions, markets or rules. Give a short reason."
)


class RouteDecision(BaseModel):
    """The model's routing decision, in a fixed shape the code can rely on."""

    route: Route = Field(description="portfolio or general")
    reason: str = Field(description="One short sentence: why this route")

# Word beginnings that point to a client's own holdings: these questions need the portfolio tools
PORTFOLIO_WORDS = (
    "allocation",
    "exposed",
    "exposure",
    "holding",
    "invested",
    "portfolio",
    "position",
    "sector",
    "stake",
    "weight",
)


def classify_question(question: str) -> Route:
    """Portfolio questions go to the tools; everything else is a general question."""
    words = re.findall(r"[a-z]+", question.lower())
    if any(word.startswith(PORTFOLIO_WORDS) for word in words):
        return "portfolio"
    return "general"
