"""The critic's fixed criteria (Lab 55): checked by code, the same answer every time."""

from sovereign_brain.graphs.team.critic import rule_problems

CASE = {
    "client_id": "C-1042",
    "question": "Could this client live with a 40% fall in energy stocks?",
    "notes": [
        {"author": "analyst", "text": "Energy is 185,000 USD, 18.5% of the portfolio."},
        {"author": "risk_officer", "text": "A 40% fall costs 74,000 USD, 7.4%; the limit is 5%."},
    ],
}


def test_a_supported_short_draft_has_no_problems() -> None:
    draft = "For C-1042, a 40% energy fall would cost 74,000 USD, 7.4% of the portfolio."

    assert rule_problems(draft, CASE) == []


def test_a_long_draft_without_the_client_id_is_sent_back() -> None:
    draft = "Energy is large. It could fall. That would hurt. The limit is 5%."

    assert rule_problems(draft, CASE) == [
        "Too long: 4 sentences, at most 3.",
        "The client ID C-1042 is missing.",
    ]


def test_a_figure_that_is_not_in_the_notes_is_named() -> None:
    draft = "For C-1042, a 40% fall would cost 74,000 USD, about 9.1% of the portfolio."

    assert rule_problems(draft, CASE) == ["The figure 9.1 is not in the notes."]
