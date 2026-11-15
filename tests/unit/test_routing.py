import pytest

from sovereign_brain.graphs.routing import classify_question


@pytest.mark.parametrize(
    ("question", "route"),
    [
        ("Summarise the exposure of this client to energy stocks.", "portfolio"),
        ("How exposed is this client to fuel prices?", "portfolio"),
        ("List the largest HOLDINGS of this client.", "portfolio"),
        ("What does a moderate risk profile mean?", "general"),
        ("Explain what a government bond is.", "general"),
        ("Is it a mistake to hold cash?", "general"),
    ],
)
def test_questions_are_routed_by_their_words(question: str, route: str) -> None:
    assert classify_question(question) == route
