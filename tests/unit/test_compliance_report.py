"""The Compliance Sentinel (Lab 95): controls are met or flagged from the evidence alone."""

import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from sovereign_brain.compliance.report import build_report, to_markdown
from sovereign_brain.security.audit_chain import GENESIS, entry_hash

POSTURE = {"injection_guard_rules": ["override_instructions"], "market_mutual_tls": True,
           "pii_masking": True}


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


def chain(rows: list[tuple[str, str, str]]) -> list[Event]:
    """Linked entries (actor, action, subject), written today, like AuditRepository.append."""
    events, prev = [], GENESIS
    for seq, (actor, action, subject) in enumerate(rows, start=1):
        at = datetime.now(UTC).isoformat(timespec="microseconds")
        digest = entry_hash(prev, at, actor, action, subject, json.dumps({}))
        events.append(Event(seq, at, actor, action, subject, json.dumps({}), prev, digest))
        prev = digest
    return events


def controls(report: dict) -> dict[str, dict]:
    return {control["rule"].split(" (")[0]: control for control in report["controls"]}


def test_a_clean_record_meets_every_control() -> None:
    events = chain([("amina", "approval.requested", "a1"), ("omar", "approval.approved", "a1")])

    report = build_report(events, POSTURE, days=30)

    assert report["all_met"] is True
    assert controls(report)["EU AI Act, Article 14"]["evidence"]["decisions"] == 1
    assert report["audit_head"] == events[-1].hash
    assert "| met |" in to_markdown(report, "c2lnbg", "8c41e2d09a7b3f15")


def test_self_approval_and_tampering_are_flagged() -> None:
    events = chain([("amina", "approval.requested", "a1"), ("amina", "approval.approved", "a1")])
    events[1] = replace(events[1], actor="omar")  # someone edits the log to hide it

    report = controls(build_report(events, POSTURE, days=30))

    assert report["EU AI Act, Article 12"]["met"] is False  # the edit breaks the chain
    events[1] = replace(events[1], actor="amina")
    report = controls(build_report(events, POSTURE, days=30))
    assert report["EU AI Act, Article 14"]["evidence"]["four_eyes_breaches"] == ["a1"]
    assert report["EU AI Act, Article 14"]["met"] is False
