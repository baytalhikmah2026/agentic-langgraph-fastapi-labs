"""What the model reads (Lab 39): the thread's messages, plus a note of related earlier answers."""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from sovereign_brain.graphs.research import MEMORY_NOTE, with_memory

NOTE = {
    "owner": "amina",
    "client_id": "C-1042",
    "thread_id": "bond-basics",
    "question": "What is a bond?",
    "answer": "A bond is a loan to a company.",
    "route": "general",
    "saved_at": "2026-11-10T09:00:00Z",
    "score": 0.82,
}
MESSAGES = [
    SystemMessage("You are an analyst."),
    HumanMessage("Client C-1042: an earlier question"),
    AIMessage("An earlier answer"),
    HumanMessage("Client C-1042: What is the risk of a bond?"),
]


def test_without_recollections_the_model_reads_the_thread() -> None:
    assert with_memory({"messages": MESSAGES, "recollections": []}) == MESSAGES


def test_the_note_sits_just_before_the_newest_question() -> None:
    messages = [*MESSAGES, AIMessage("A draft"), HumanMessage("Revise.", name="reviewer")]

    seen = with_memory({"messages": messages, "recollections": [NOTE]})

    assert len(seen) == len(messages) + 1
    assert seen[3].type == "system"
    expected = "- 2026-11-10 Q: What is a bond? A: A bond is a loan to a company."
    assert seen[3].content == MEMORY_NOTE + expected
    assert seen[4] is messages[3]  # then the newest question, the draft and the review note


def test_a_malformed_recollection_is_left_out() -> None:
    broken = {**NOTE, "client_id": "not-a-client"}

    assert with_memory({"messages": MESSAGES, "recollections": [broken]}) == MESSAGES
