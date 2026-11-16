"""The audit trail of a research run (Lab 26): one entry per station, never rewritten."""

from datetime import UTC, datetime
from typing import TypedDict


class TrailEntry(TypedDict):
    """One line of the trail: which station, what it decided, and when (UTC)."""

    node: str
    note: str
    at: str


def mark(node: str, note: str) -> list[TrailEntry]:
    """A one-entry list, ready for the operator.add reducer to append to the trail."""
    at = datetime.now(UTC).isoformat(timespec="milliseconds")
    return [{"node": node, "note": note, "at": at}]


def stations(trail: list[TrailEntry]) -> list[str]:
    """Only the station names, in the order the request passed them."""
    return [entry["node"] for entry in trail]
