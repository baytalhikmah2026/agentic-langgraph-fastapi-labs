"""The Sovereign Enterprise Brain's contracts (Lab 97): every message between its agents.

The capstone team is hierarchical. A supervisor hands the work to three specialists, in an
order of trust:
1. extraction:   facts from the desk's own tools (positions, prices, research notes);
2. sanitization: personal data masked and injected text quarantined (Labs 71-72);
3. analysis:     the model writes a brief from the clean facts only.
Every hand-over has a schema, so each agent can rely on what it receives, the graph's state
stays valid, and the API can stream each step safely to the analyst.
"""

import unicodedata
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from sovereign_brain.security.injection import injection_rules

Agent = Literal["extraction", "sanitization", "analysis"]
Closed = ConfigDict(extra="forbid", str_strip_whitespace=True)  # unknown fields are refused
Sector = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z &-]{1,39}$")]  # Lab 99: names only


class BrainRequest(BaseModel):
    """What an analyst asks the Brain (the only part that comes from outside)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)

    client_id: str = Field(pattern=r"^C-\d{4}$", examples=["C-1042"])
    question: str = Field(min_length=10, max_length=1000)
    sectors: list[Sector] = Field(default_factory=list, max_length=5)  # optional focus

    @field_validator("question")
    @classmethod
    def plain_question(cls, question: str) -> str:
        """Lab 99: the door checks the question itself, before any agent sees it."""
        if any(unicodedata.category(char) == "Cc" and char not in "\n\t" for char in question):
            raise ValueError("The question contains control characters")
        if injection_rules(question):  # the guard from Lab 71, now part of the contract
            raise ValueError("The question contains instructions for the model")
        return question


class SupervisorDecision(BaseModel):
    """The supervisor's choice: which specialist works next, or finish."""

    model_config = Closed

    next: Agent | Literal["finish"]
    reason: str = Field(max_length=300)


class Holding(BaseModel):
    model_config = Closed

    ticker: str = Field(pattern=r"^[A-Z0-9]{2,12}$")
    name: str = Field(max_length=80)
    sector: str = Field(max_length=40)
    market_value_usd: int = Field(ge=0)
    price_usd: float | None = Field(default=None, gt=0)


class ExtractedFacts(BaseModel):
    """Extraction's result: only facts the desk's tools returned, with their sources."""

    model_config = Closed

    client_id: str = Field(pattern=r"^C-\d{4}$")
    holdings: list[Holding] = Field(max_length=50)
    portfolio_value_usd: int = Field(ge=0)
    notes: list[str] = Field(default_factory=list, max_length=5)
    sources: list[str] = Field(min_length=1)


class SanitizedFacts(BaseModel):
    """Sanitization's result: the same facts, safe for the model to read."""

    model_config = Closed

    facts: ExtractedFacts
    masked_values: int = Field(ge=0)
    quarantined_notes: int = Field(ge=0)


class Figure(BaseModel):
    model_config = Closed

    label: str = Field(max_length=80)
    value: float
    unit: Literal["USD", "%"]


class AnalysisDraft(BaseModel):
    """Analysis's result: the brief, its figures and risks, in a shape code can check."""

    model_config = Closed

    summary: str = Field(min_length=20, max_length=1500)
    figures: list[Figure] = Field(default_factory=list, max_length=10)
    risks: list[str] = Field(default_factory=list, max_length=5)
    confidence: float = Field(ge=0, le=1)


class BrainEvent(BaseModel):
    """One message on the Brain's live channel (Lab 98), from start to delivery."""

    model_config = Closed

    type: Literal["started", "agent", "approval_needed", "delivered", "rejected", "error"]
    run_id: str
    agent: Agent | Literal["supervisor"] | None = None
    data: dict = Field(default_factory=dict)
    at: datetime


def supported_values(facts: ExtractedFacts) -> set[float]:
    """Every USD amount the facts can back: each holding, each sector's total, the portfolio."""
    sectors: dict[str, int] = {}
    for holding in facts.holdings:
        sectors[holding.sector] = sectors.get(holding.sector, 0) + holding.market_value_usd
    values = {float(h.market_value_usd) for h in facts.holdings}
    values |= {float(h.price_usd) for h in facts.holdings if h.price_usd is not None}
    return values | {float(v) for v in sectors.values()} | {float(facts.portfolio_value_usd)}


def unsupported_figures(draft: AnalysisDraft, facts: ExtractedFacts) -> list[Figure]:
    """Figures the facts don't back: a USD amount nobody reported, or a % outside 0-100."""
    known = supported_values(facts)
    return [
        figure
        for figure in draft.figures
        if (figure.unit == "USD" and figure.value not in known)
        or (figure.unit == "%" and not 0 <= figure.value <= 100)
    ]


SCHEMAS: dict[str, type[BaseModel]] = {
    "BrainRequest": BrainRequest,
    "SupervisorDecision": SupervisorDecision,
    "ExtractedFacts": ExtractedFacts,
    "SanitizedFacts": SanitizedFacts,
    "AnalysisDraft": AnalysisDraft,
    "BrainEvent": BrainEvent,
}
