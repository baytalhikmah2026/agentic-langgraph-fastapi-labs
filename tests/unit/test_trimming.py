"""A long thread, a short view (Lab 40): the model reads only the newest part of a thread."""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from sovereign_brain.graphs.research import with_memory


def turn(n: int) -> list:
    return [HumanMessage(f"Question {n}"), AIMessage(f"Answer {n}")]


MESSAGES = [SystemMessage("You are an analyst."), *turn(1), *turn(2), *turn(3)]


def test_older_turns_are_trimmed_to_the_limit() -> None:
    state = {"messages": [*MESSAGES, HumanMessage("Question 4")], "recollections": []}

    seen = with_memory(state, history_limit=3)

    contents = [m.content for m in seen]
    assert contents == ["You are an analyst.", "Question 3", "Answer 3", "Question 4"]


def test_the_current_turn_is_never_cut() -> None:
    current = [
        HumanMessage("Question 4"),
        AIMessage("A draft with a wrong figure"),
        HumanMessage("Revise your answer.", name="reviewer"),
    ]
    state = {"messages": [*MESSAGES, *current], "recollections": []}

    seen = with_memory(state, history_limit=1)

    assert [m.content for m in seen] == ["You are an analyst.", *[m.content for m in current]]
