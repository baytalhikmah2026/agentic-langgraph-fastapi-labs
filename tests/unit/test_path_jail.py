"""The path jail of the notes server (Lab 45): no name may lead outside the notes folder."""

from pathlib import Path

import pytest

from sovereign_brain.mcp_servers.notes import PathJailError, jailed_path


@pytest.mark.parametrize(
    "name",
    [
        "../secrets.md",  # one folder up
        "../../../private/keys.md",  # many folders up
        "/srv/secrets.md",  # an absolute path
        "gulf-petroleum.txt",  # not a Markdown note
    ],
)
def test_names_outside_the_jail_are_refused(tmp_path: Path, name: str) -> None:
    root = tmp_path / "research_notes"
    root.mkdir()

    with pytest.raises(PathJailError):
        jailed_path(root, name)


def test_a_note_in_a_subfolder_is_allowed(tmp_path: Path) -> None:
    root = tmp_path / "research_notes"

    assert jailed_path(root, "2026/q1-review.md") == (root / "2026" / "q1-review.md").resolve()
