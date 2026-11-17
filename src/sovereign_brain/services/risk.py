"""The corporate risk calculator (Lab 41): plain Python, no AI, the same answer every time.

A stress test asks one question: if every stock in one sector fell by a given percent, how
much of the whole portfolio would be lost, and does the client's risk profile accept that?
"""

from typing import Literal

from pydantic import BaseModel

RiskProfile = Literal["conservative", "moderate", "growth", "aggressive"]

# The largest loss from one sector shock that each risk profile accepts, in % of the portfolio
LOSS_LIMITS: dict[RiskProfile, float] = {
    "conservative": 2.0,
    "moderate": 5.0,
    "growth": 8.0,
    "aggressive": 10.0,
}


class StressResult(BaseModel):
    """The calculator's answer: every figure the model may quote about a stress test."""

    client_id: str
    sector: str
    shock_percent: float
    loss_usd: float
    loss_percent: float  # of the whole portfolio
    limit_percent: float  # the most this risk profile accepts
    verdict: Literal["within limit", "limit breached"]


def stress_test(
    client_id: str,
    sector: str,
    sector_value_usd: float,
    portfolio_value_usd: float,
    shock_percent: float,
    risk_profile: RiskProfile,
) -> StressResult:
    """Apply a price fall of `shock_percent` to one sector and compare the loss with the limit."""
    loss = round(sector_value_usd * shock_percent / 100, 2)
    loss_percent = round(100 * loss / portfolio_value_usd, 1)
    limit = LOSS_LIMITS[risk_profile]
    return StressResult(
        client_id=client_id,
        sector=sector,
        shock_percent=shock_percent,
        loss_usd=loss,
        loss_percent=loss_percent,
        limit_percent=limit,
        verdict="within limit" if loss_percent <= limit else "limit breached",
    )
