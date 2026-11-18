"""The report's facts and rules (Labs 49, 64): plain code, no model."""

from sovereign_brain.graphs.report import (
    fallback_report,
    report_brief,
    report_problems,
    sector_facts,
)
from sovereign_brain.schemas.report import ResearchReport

PORTFOLIO = {
    "client_id": "C-1042",
    "positions": [
        {"ticker": "MDNB", "name": "Medina Bank", "sector": "Financials",
         "market_value_usd": 815000},
        {"ticker": "GLFP", "name": "Gulf Petroleum Co", "sector": "Energy",
         "market_value_usd": 120000},
        {"ticker": "SNRS", "name": "Sunrise Solar", "sector": "Energy",
         "market_value_usd": 65000},
    ],
}


def test_sectors_are_totalled_largest_first() -> None:
    facts = sector_facts(PORTFOLIO)

    assert facts["portfolio_value_usd"] == 1000000
    assert facts["sectors"] == [
        {"sector": "Financials", "value_usd": 815000, "percent": 81.5},
        {"sector": "Energy", "value_usd": 185000, "percent": 18.5},
    ]


def test_the_plain_report_always_matches_the_facts() -> None:
    facts = sector_facts(PORTFOLIO)

    report = fallback_report("C-1042", facts)

    assert report.risk_level == "high"
    assert report_problems(report, facts) == []


def test_every_mismatch_is_listed() -> None:
    facts = sector_facts(PORTFOLIO)
    report = ResearchReport(
        client_id="C-1042",
        headline="Energy is the largest sector at 25% of the portfolio.",
        largest_sector="Energy",
        largest_sector_percent=25,
        risk_level="medium",
        key_points=["Energy holdings total 185000 USD.", "Medina Bank is a large position."],
    )

    assert report_problems(report, facts) == [
        "largest_sector must be Financials",
        "largest_sector_percent must be 81.5",
        "risk_level must be high",
        "these figures are not in the facts: 25",
    ]


def test_reviewer_notes_reach_the_next_brief() -> None:
    state = {
        "client_id": "C-1042",
        "client_profile": "Amina Rahman Holdings, private-banking, risk profile moderate",
        "facts": sector_facts(PORTFOLIO),
        "problems": [],
        "feedback": ["omar: Mention both energy holdings by name."],
    }

    brief = report_brief(state)

    assert brief.endswith(
        "Reviewer notes (follow them where the facts allow): "
        "omar: Mention both energy holdings by name."
    )
