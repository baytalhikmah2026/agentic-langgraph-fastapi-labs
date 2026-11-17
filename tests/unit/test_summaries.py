"""The text a thread summary is written from (Lab 40)."""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from sovereign_brain.memory.summaries import conversation_text


def test_only_questions_and_answers_are_summarised() -> None:
    messages = [
        SystemMessage("You are an analyst."),
        HumanMessage("Client C-1042: How large is the energy exposure?"),
        AIMessage("", tool_calls=[{"name": "sector_exposure", "args": {}, "id": "call-1"}]),
        ToolMessage('{"percent": 18.5}', tool_call_id="call-1"),
        AIMessage("Energy is 18.5% of the portfolio."),
        HumanMessage("Revise your answer.", name="reviewer"),
    ]

    assert conversation_text(messages) == (
        "Analyst: Client C-1042: How large is the energy exposure?\n"
        "Research Desk: Energy is 18.5% of the portfolio."
    )
