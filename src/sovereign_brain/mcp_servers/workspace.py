"""The project-workspace MCP server (Lab 60): where the agency's developer writes real files.

Only Python and Markdown files, only inside one folder, at most 20,000 characters each.
Every write is appended to an audit file, like the notes server (Lab 45).

Run it on its own with: uv run python -m sovereign_brain.mcp_servers.workspace
"""

import os
from pathlib import Path
from typing import Annotated

import anyio
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from sovereign_brain.mcp_servers.notes import PathJailError, write_audit

WORKSPACE_DIR = Path(os.environ.get("SB_WORKSPACE_DIR", "data/workspace"))
AUDIT_FILE = Path(os.environ.get("SB_WORKSPACE_AUDIT_FILE", "data/audit/workspace_audit.jsonl"))
MAX_FILE_CHARS = 20_000
ALLOWED_SUFFIXES = (".py", ".md")

FileName = Annotated[
    str, Field(min_length=4, max_length=120, description="A file name, e.g. sector_weights.py")
]


def workspace_path(root: Path, name: str) -> Path:
    """The file for a name, always inside `root` and always .py or .md; anything else refused."""
    if not name.endswith(ALLOWED_SUFFIXES):
        raise PathJailError(f"Only .py and .md files are allowed: {name!r}")
    base = root.resolve()
    target = (base / name).resolve()
    if not target.is_relative_to(base):
        raise PathJailError(f"{name!r} is outside the workspace")
    return target


def create_server(root: Path, audit_file: Path) -> FastMCP:
    """A workspace server for one folder (tests use a temporary folder)."""
    server = FastMCP(
        "project-workspace",
        instructions="The project workspace of the Research Desk's software agency.",
    )

    @server.tool()
    async def list_files() -> list[str]:
        """The names of all files in the workspace."""
        base = root.resolve()
        return sorted(
            path.relative_to(base).as_posix()
            for path in base.rglob("*")
            if path.suffix in ALLOWED_SUFFIXES
        )

    @server.tool()
    async def read_file(name: FileName) -> str:
        """The full text of one workspace file. Use list_files to see the names."""
        path = anyio.Path(workspace_path(root, name))
        if not await path.is_file():
            raise ValueError(f"No file named {name!r}. Use list_files to see the names.")
        return await path.read_text(encoding="utf-8")

    @server.tool()
    async def write_file(
        name: FileName,
        text: Annotated[str, Field(min_length=1, max_length=MAX_FILE_CHARS)],
    ) -> str:
        """Create or replace one workspace file with the given text."""
        path = anyio.Path(workspace_path(root, name))
        action = "update" if await path.exists() else "create"
        await path.parent.mkdir(parents=True, exist_ok=True)
        await path.write_text(text, encoding="utf-8")
        write_audit(audit_file, action, name, len(text))
        return f"Saved {name} ({len(text)} characters)"

    return server


server = create_server(WORKSPACE_DIR, AUDIT_FILE)

if __name__ == "__main__":
    server.run()
