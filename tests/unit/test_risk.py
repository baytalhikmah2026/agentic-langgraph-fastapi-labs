"""The corporate risk calculator and its strict tool form (Lab 41)."""

import pytest
from pydantic import ValidationError

from sovereign_brain.services.risk import stress_test
from sovereign_brain.tools.risk import stress_test_tool

GOOD = {
    "client_id": "C-1042",
    "sector": "Energy",
    "sector_value_usd": 185000,
    "portfolio_value_usd": 1000000,
    "shock_percent": 40,
    "risk_profile": "moderate",
}


def test_a_small_shock_stays_within_the_limit() -> None:
    result = stress_test("C-1042", "Energy", 185000, 1000000, 20, "moderate")

    assert result.loss_usd == 37000
    assert result.loss_percent == 3.7
    assert result.limit_percent == 5.0
    assert result.verdict == "within limit"


def test_a_large_shock_breaches_the_limit() -> None:
    result = stress_test("C-1042", "Energy", 185000, 1000000, 40, "moderate")

    assert result.loss_usd == 74000
    assert result.loss_percent == 7.4
    assert result.verdict == "limit breached"


def test_the_tool_runs_the_calculator_for_a_correct_form() -> None:
    result = stress_test_tool.invoke(GOOD)

    assert result["loss_usd"] == 74000
    assert result["verdict"] == "limit breached"


@pytest.mark.parametrize(
    "change",
    [
        {"client_id": "1042"},  # not the C-NNNN pattern
        {"shock_percent": 120},  # prices cannot fall by more than 90% in this calculator
        {"risk_profile": "reckless"},  # not one of the four profiles
        {"sector_value_usd": 2000000},  # larger than the whole portfolio
        {"currency": "EUR"},  # a field the form does not have
    ],
)
def test_a_malformed_form_never_reaches_the_calculator(change: dict) -> None:
    with pytest.raises(ValidationError):
        stress_test_tool.invoke({**GOOD, **change})


def test_the_field_descriptions_reach_the_model() -> None:
    fields = stress_test_tool.args

    assert set(fields) == set(GOOD)
    assert "sector_exposure" in fields["sector_value_usd"]["description"]
    assert fields["shock_percent"]["exclusiveMinimum"] == 0
