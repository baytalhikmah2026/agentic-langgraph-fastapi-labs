"""The stress-test tool (Lab 41): a strict Pydantic form in front of the risk calculator.

The model never does the arithmetic. It only fills in the form below. Pydantic checks every
field before the calculator runs, and the Field descriptions tell the model how to fill it.
"""

from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field, model_validator

from sovereign_brain.services.risk import RiskProfile, stress_test


class StressTestInput(BaseModel):
    """The form the model fills in to request a stress test."""

    model_config = ConfigDict(extra="forbid")  # an invented extra field is an error

    client_id: str = Field(
        pattern=r"^C-\d{4}$", description="The client ID from the brief, for example C-1042"
    )
    sector: str = Field(
        min_length=2, max_length=40, description="The sector to shock, for example Energy"
    )
    sector_value_usd: float = Field(
        ge=0, description="Value held in the sector in US dollars, as returned by sector_exposure"
    )
    portfolio_value_usd: float = Field(
        gt=0, description="Total portfolio value in US dollars, as returned by sector_exposure"
    )
    shock_percent: float = Field(
        gt=0, le=90, description="The assumed price fall in percent, for example 30 for a 30% fall"
    )
    risk_profile: RiskProfile = Field(
        description="The client's risk profile, as written in the client brief"
    )

    @model_validator(mode="after")
    def sector_fits_in_portfolio(self) -> "StressTestInput":
        """A sector can never be worth more than the whole portfolio."""
        if self.sector_value_usd > self.portfolio_value_usd:
            raise ValueError("sector_value_usd cannot be larger than portfolio_value_usd")
        return self


@tool("stress_test", args_schema=StressTestInput)
def stress_test_tool(
    client_id: str,
    sector: str,
    sector_value_usd: float,
    portfolio_value_usd: float,
    shock_percent: float,
    risk_profile: RiskProfile,
) -> dict:
    """Loss if one sector fell by shock_percent, and whether the risk profile accepts it."""
    result = stress_test(
        client_id, sector, sector_value_usd, portfolio_value_usd, shock_percent, risk_profile
    )
    return result.model_dump()


RISK_TOOLS = [stress_test_tool]
