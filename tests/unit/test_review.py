from sovereign_brain.graphs.review import unsupported_figures

TOOL_RESULT = (
    '{"client_id": "C-1042", "sector": "Energy", "sector_value_usd": 185000, '
    '"portfolio_value_usd": 1000000, "percent": 18.5}'
)


def test_figures_from_the_tools_are_accepted_in_any_format() -> None:
    answer = "Energy is 18.5% of C-1042's portfolio: USD 185,000 of USD 1,000,000 in 2 holdings."

    assert unsupported_figures(answer, TOOL_RESULT) == []


def test_figures_not_in_the_tools_are_reported_as_written() -> None:
    answer = "Energy is 25% of the portfolio, about USD 250,000."

    assert unsupported_figures(answer, TOOL_RESULT) == ["25", "250,000"]


def test_an_answer_without_figures_has_nothing_to_check() -> None:
    assert unsupported_figures("Energy is a modest part of the portfolio.", TOOL_RESULT) == []
