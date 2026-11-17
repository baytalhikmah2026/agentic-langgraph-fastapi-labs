"""The research-notes MCP server (Lab 45): the desk's notes folder, behind a path jail.

The agent may list, read and save Markdown notes, but only inside one folder. Every name is
checked before any file is touched, so "../secrets.md" or "/srv/secrets.md" never get through. Every
read and every change is appended to an audit file, one JSON line each.

Run it on its own with: uv run python -m sovereign_brain.mcp_servers.notes
"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import anyio
from mcp.server.fastmcp import FastMCP
from pydantic import Field

NOTES_DIR = Path(os.environ.get("SB_NOTES_DIR", "data/research_notes"))
AUDIT_FILE = Path(os.environ.get("SB_NOTES_AUDIT_FILE", "data/audit/notes_audit.jsonl"))
MAX_NOTE_CHARS = 20_000

NoteName = Annotated[
    str, Field(min_length=4, max_length=120, description="A note file name, e.g. gulf-petroleum.md")
]


class PathJailError(ValueError):
    """A note name that would leave the notes folder, or is not a Markdown note."""


def jailed_path(root: Path, name: str) -> Path:
    """The file for a note name, always inside `root`; anything else is refused."""
    if not name.endswith(".md"):
        raise PathJailError(f"Only Markdown notes (.md) are allowed: {name!r}")
    base = root.resolve()
    target = (base / name).resolve()  # resolve() follows "..", links and absolute paths
    if not target.is_relative_to(base):
        raise PathJailError(f"{name!r} is outside the notes folder")
    return target


def write_audit(audit_file: Path, action: str, name: str, chars: int) -> None:
    """Append one line to the audit file: when, what, which note, how many characters."""
    audit_file.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "at": datetime.now(UTC).isoformat(timespec="seconds"),
        "action": action,
        "note": name,
        "chars": chars,
    }
    with audit_file.open("a", encoding="utf-8") as log:
        log.write(json.dumps(entry) + "\n")


def create_server(root: Path, audit_file: Path) -> FastMCP:
    """A notes server for one folder (tests use a temporary folder)."""
    server = FastMCP(
        "research-notes",
        instructions="The research notes of the Crescent Ledger Bank Research Desk.",
    )

    @server.tool()
    async def list_notes() -> list[str]:
        """The names of all research notes, for example gulf-petroleum.md."""
        base = root.resolve()
        return sorted(path.relative_to(base).as_posix() for path in base.rglob("*.md"))

    @server.tool()
    async def read_note(name: NoteName) -> str:
        """The full text of one research note. Use list_notes to see the names."""
        path = anyio.Path(jailed_path(root, name))
        if not await path.is_file():
            raise ValueError(f"No note named {name!r}. Use list_notes to see the names.")
        text = await path.read_text(encoding="utf-8")
        write_audit(audit_file, "read", name, len(text))
        return text

    @server.tool()
    async def save_note(
        name: NoteName,
        text: Annotated[str, Field(min_length=1, max_length=MAX_NOTE_CHARS)],
    ) -> str:
        """Create or replace a research note with the given Markdown text."""
        path = anyio.Path(jailed_path(root, name))
        action = "update" if await path.exists() else "create"
        await path.parent.mkdir(parents=True, exist_ok=True)
        await path.write_text(text, encoding="utf-8")
        write_audit(audit_file, action, name, len(text))
        return f"Saved {name} ({len(text)} characters)"

    return server


server = create_server(NOTES_DIR, AUDIT_FILE)

if __name__ == "__main__":
    server.run()
