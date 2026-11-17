"""Semantic memory in an in-process Qdrant (Lab 38): store answers, find them by meaning."""

from collections.abc import Callable

from sovereign_brain.memory.semantic import MemoryRecord, SemanticMemory


def record(owner: str, question: str, answer: str, client_id: str = "C-1042") -> MemoryRecord:
    return MemoryRecord(
        owner=owner,
        client_id=client_id,
        thread_id="energy-review",
        question=question,
        answer=answer,
        route="general",
    )


async def test_a_related_question_finds_the_stored_answer(
    make_memory: Callable[[], SemanticMemory],
) -> None:
    memory = make_memory()
    await memory.remember(record("amina", "What is a bond?", "A bond is a loan to a company."))
    await memory.remember(
        record("amina", "How large is the energy exposure?", "Energy is 18.5% of the portfolio.")
    )

    found = await memory.recall("amina", "C-1042", "Tell me again about energy exposure")

    assert [r.question for r in found] == ["How large is the energy exposure?"]
    assert 0.5 <= found[0].score <= 1.0


async def test_memories_stay_with_their_analyst_and_client(
    make_memory: Callable[[], SemanticMemory],
) -> None:
    memory = make_memory()
    await memory.remember(record("amina", "Energy exposure?", "Energy is 18.5%."))
    await memory.remember(record("omar", "Energy exposure?", "Energy is 20.0%."))
    await memory.remember(record("amina", "Energy exposure?", "Energy is 10.0%.", "C-2077"))

    found = await memory.recall("amina", "C-1042", "energy exposure")

    assert [r.answer for r in found] == ["Energy is 18.5%."]


async def test_an_unrelated_question_finds_nothing(
    make_memory: Callable[[], SemanticMemory],
) -> None:
    memory = make_memory()
    await memory.remember(record("amina", "What is a bond?", "A bond is a loan to a company."))

    assert await memory.recall("amina", "C-1042", "What is the energy exposure?") == []
