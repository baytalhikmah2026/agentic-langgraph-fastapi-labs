"""The hash-chained audit log (Lab 77): edits, removals and backdating are all found."""

import json
from dataclasses import dataclass, replace

from sovereign_brain.security.audit_chain import GENESIS, entry_hash, verify_chain


@dataclass(frozen=True)
class Event:
    seq: int
    at: str
    actor: str
    action: str
    subject: str
    details: str
    prev_hash: str
    hash: str


def build_chain() -> list[Event]:
    """Three linked entries, the way AuditRepository.append writes them."""
    rows = [
        ("2026-11-18T10:00:00.000000+00:00", "amina", "approval.requested", {"client": "C-1042"}),
        ("2026-11-18T10:05:00.000000+00:00", "omar", "approval.sent_back", {"comment": "Name it"}),
        ("2026-11-18T10:09:00.000000+00:00", "omar", "approval.approved", {"comment": None}),
    ]
    chain, prev = [], GENESIS
    for seq, (at, actor, action, details) in enumerate(rows, start=1):
        text = json.dumps(details, sort_keys=True)
        digest = entry_hash(prev, at, actor, action, "a1", text)
        chain.append(Event(seq, at, actor, action, "a1", text, prev, digest))
        prev = digest
    return chain


def test_an_untouched_chain_is_intact() -> None:
    assert verify_chain(build_chain()) == []


def test_an_edited_entry_is_found() -> None:
    chain = build_chain()
    chain[1] = replace(chain[1], actor="amina")  # someone rewrites who sent it back

    assert verify_chain(chain) == ["event 2: hash does not match its content (edited)"]


def test_a_removed_entry_is_found() -> None:
    chain = build_chain()
    del chain[1]

    assert verify_chain(chain) == ["event 3: does not follow event 1 (an entry is missing)"]


def test_a_backdated_entry_is_found() -> None:
    chain = build_chain()
    early = "2026-11-18T09:00:00.000000+00:00"
    text = chain[2].details
    forged = entry_hash(chain[2].prev_hash, early, "omar", "approval.approved", "a1", text)
    chain[2] = replace(chain[2], at=early, hash=forged)  # even with a freshly made hash

    assert verify_chain(chain) == ["event 3: dated before event 2 (backdated)"]
