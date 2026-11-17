"""Long documents for analysis (Lab 57): read only from one folder, nothing outside it."""

from pathlib import Path


class DocumentNotFound(LookupError):
    """No document with this name in the documents folder."""


def list_documents(folder: Path) -> list[str]:
    """The names of the Markdown documents in the folder, in alphabetical order."""
    return sorted(path.name for path in folder.glob("*.md"))


def load_document(folder: Path, name: str) -> str:
    """The text of one document; a name that leads outside the folder is never read."""
    root = folder.resolve()
    path = (root / name).resolve()
    if not path.is_relative_to(root) or not path.is_file():  # the path jail from Lab 45
        raise DocumentNotFound(name)
    return path.read_text(encoding="utf-8")


def chunk_text(text: str, size: int) -> list[str]:
    """Paragraphs packed into pieces of at most `size` characters; long paragraphs are cut."""
    pieces: list[str] = []
    current = ""
    for paragraph in (p.strip() for p in text.split("\n\n")):
        if not paragraph:
            continue
        if current and len(current) + 2 + len(paragraph) <= size:
            current += "\n\n" + paragraph
            continue
        if current:
            pieces.append(current)
        while len(paragraph) > size:  # one paragraph larger than a whole piece
            pieces.append(paragraph[:size])
            paragraph = paragraph[size:]
        current = paragraph
    if current:
        pieces.append(current)
    return pieces


def group_texts(texts: list[str], limit: int) -> list[str]:
    """Neighbouring texts joined into groups of at most `limit` characters each."""
    groups: list[str] = []
    for text in texts:
        if groups and len(groups[-1]) + 2 + len(text) <= limit:
            groups[-1] += "\n\n" + text
        else:
            groups.append(text)
    return groups
