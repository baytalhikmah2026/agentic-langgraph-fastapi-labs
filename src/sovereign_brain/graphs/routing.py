"""Routing rules for the research graph (Lab 23): which track does a question take?"""

import re
from typing import Literal

Route = Literal["general", "portfolio"]

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
