"""The brief that a correction replaces (Lab 37)."""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from sovereign_brain.memory.corrections import latest_brief


def test_the_latest_brief_skips_review_notes() -> None:
    messages = [
        SystemMessage("You are an analyst."),
        HumanMessage("Client C-1042: first question", id="q1"),
        AIMessage("First answer"),
        HumanMessage("Client C-1042: second question", id="q2"),
        AIMessage("Draft with a wrong figure"),
        HumanMessage("Revise your answer.", name="reviewer"),
    ]

    assert latest_brief(messages).id == "q2"
