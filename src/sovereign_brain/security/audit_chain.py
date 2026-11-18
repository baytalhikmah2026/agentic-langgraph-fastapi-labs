"""A hash-chained audit log (Lab 77): each entry carries the fingerprint of the one before it.

Change, remove or reorder one entry, and every later link stops matching. The verifier walks
the whole chain and names each problem: edited content, a broken link (a removed entry), or
an entry dated earlier than the one before it (backdating). DORA asks banks for logs whose
integrity they can prove; this is the core of that proof.
"""

import hashlib
import json
from typing import Protocol

from sovereign_brain.security.signing import canonical

GENESIS = "0" * 64  # the "previous hash" of the very first entry


class ChainEvent(Protocol):
    """What the verifier reads from each stored entry."""

    seq: int
    at: str
    actor: str
    action: str
    subject: str
    details: str
    prev_hash: str
    hash: str


def entry_hash(prev_hash: str, at: str, actor: str, action: str, subject: str, details: str) -> str:
    """The fingerprint of one entry, including the fingerprint of the entry before it."""
    content = {
        "prev_hash": prev_hash,
        "at": at,
        "actor": actor,
        "action": action,
        "subject": subject,
        "details": json.loads(details),
    }
    return hashlib.sha256(canonical(content)).hexdigest()


def verify_chain(events: list[ChainEvent]) -> list[str]:
    """Every problem in the chain, oldest first; an empty list means the log is intact."""
    problems = []
    previous: ChainEvent | None = None
    for event in events:
        expected_prev = previous.hash if previous else GENESIS
        if event.prev_hash != expected_prev:
            after = f"event {previous.seq}" if previous else "the start"
            problems.append(f"event {event.seq}: does not follow {after} (an entry is missing)")
        recomputed = entry_hash(
            event.prev_hash, event.at, event.actor, event.action, event.subject, event.details
        )
        if event.hash != recomputed:
            problems.append(f"event {event.seq}: hash does not match its content (edited)")
        if previous and event.at < previous.at:
            problems.append(f"event {event.seq}: dated before event {previous.seq} (backdated)")
        previous = event
    return problems
