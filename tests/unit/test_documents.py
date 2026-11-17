"""Long documents (Lab 57): splitting into pieces, grouping summaries, the folder jail."""

from pathlib import Path

import pytest

from sovereign_brain.services.documents import (
    DocumentNotFound,
    chunk_text,
    group_texts,
    load_document,
)


def test_paragraphs_are_packed_into_pieces_of_limited_size() -> None:
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."

    pieces = chunk_text(text, size=40)

    assert pieces == ["First paragraph.\n\nSecond paragraph.", "Third paragraph."]


def test_a_paragraph_longer_than_a_piece_is_cut() -> None:
    assert chunk_text("a" * 25, size=10) == ["a" * 10, "a" * 10, "a" * 5]


def test_summaries_are_grouped_with_their_neighbours() -> None:
    texts = ["x" * 20, "y" * 20, "z" * 20]

    assert group_texts(texts, limit=50) == ["x" * 20 + "\n\n" + "y" * 20, "z" * 20]


def test_a_name_outside_the_folder_is_never_read(tmp_path: Path) -> None:
    (tmp_path / "documents").mkdir()
    (tmp_path / "secret.md").write_text("Not for the agent.", encoding="utf-8")

    with pytest.raises(DocumentNotFound):
        load_document(tmp_path / "documents", "../secret.md")
