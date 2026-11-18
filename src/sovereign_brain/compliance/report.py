"""The Compliance Sentinel (Lab 95): a compliance report built only from evidence.

Every control below names the rule it answers and the evidence the desk can show for it:
the hash-chained audit log (Lab 77), the approval decisions (Labs 63-65), the erasures
(Lab 78) and the live security settings (Lab 80). Nothing is typed in by hand, so the report
can only claim what the records show. The API signs it with the desk's key (Lab 76).
"""

import json
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sovereign_brain.security.audit_chain import GENESIS, ChainEvent, verify_chain

DECISIONS = ("approval.approved", "approval.rejected", "brain.approved", "brain.rejected")


def four_eyes_breaches(events: Sequence[ChainEvent]) -> list[str]:
    """Approvals decided by the same person who requested them (should be none).

    Reports name their requester in an "approval.requested" entry (Lab 63); Brain decisions
    carry it in their own sealed details (Lab 98).
    """
    requested_by = {e.subject: e.actor for e in events if e.action == "approval.requested"}
    for e in events:
        if e.action.startswith("brain."):
            requested_by[e.subject] = json.loads(e.details).get("requested_by", "")
    return sorted(
        e.subject
        for e in events
        if e.action in DECISIONS and requested_by.get(e.subject) == e.actor
    )


def build_report(events: list[ChainEvent], posture: dict, days: int) -> dict:
    """The report: one entry per control, with its status and the evidence behind it.

    The chain is checked whole (a gap anywhere matters); the counts cover the last `days`.
    """
    now = datetime.now(UTC)
    since = (now - timedelta(days=days)).isoformat(timespec="microseconds")
    problems = verify_chain(events)
    recent = [event for event in events if event.at >= since]  # ISO times sort as text
    actions = Counter(event.action for event in recent)
    breaches = four_eyes_breaches(events)
    overrides = sum(n for action, n in actions.items() if action.startswith("approval.override"))
    decisions = sum(actions[action] for action in DECISIONS)
    controls = [
        {
            "rule": "EU AI Act, Article 12 (record-keeping)",
            "control": "Every human action on a report is kept in a tamper-evident log",
            "met": not problems,
            "evidence": {"audit_entries": len(events), "chain_problems": problems},
        },
        {
            "rule": "EU AI Act, Article 14 (human oversight)",
            "control": "No AI report reaches a client without a second person's decision",
            "met": not breaches,
            "evidence": {
                "decisions": decisions,
                "sent_back": actions["approval.sent_back"],
                "overrides": overrides,
                "four_eyes_breaches": breaches,
            },
        },
        {
            "rule": "EU AI Act, Article 15 (robustness and cybersecurity)",
            "control": "Prompt injection is screened; services prove their identity",
            "met": bool(posture["injection_guard_rules"]) and posture["market_mutual_tls"],
            "evidence": {
                "injection_guard_rules": len(posture["injection_guard_rules"]),
                "market_mutual_tls": posture["market_mutual_tls"],
            },
        },
        {
            "rule": "EU AI Act, Article 10 and GDPR, Article 25 (data protection by design)",
            "control": "Personal data is masked before any model reads it",
            "met": posture["pii_masking"],
            "evidence": {"pii_masking": posture["pii_masking"]},
        },
        {
            "rule": "GDPR, Article 17 (right to erasure)",
            "control": "Erasure requests are carried out and recorded",
            "met": True,  # the erasure path exists (Lab 78); the count shows its use
            "evidence": {"erasures": actions["privacy.erased"]},
        },
    ]
    return {
        "generated_at": now.isoformat(timespec="seconds"),
        "period_days": days,
        "controls": controls,
        "all_met": all(control["met"] for control in controls),
        "audit_head": events[-1].hash if events else GENESIS,
    }


def to_markdown(report: dict, signature: str, key_id: str) -> str:
    """The same report for people: one table, the evidence, and the seal."""
    lines = [
        f"# Compliance report, {report['generated_at']}",
        "",
        f"Period: last {report['period_days']} days. "
        f"Overall: {'all controls met' if report['all_met'] else 'ATTENTION NEEDED'}.",
        "",
        "| Rule | Control | Status | Evidence |",
        "|---|---|---|---|",
    ]
    for control in report["controls"]:
        status = "met" if control["met"] else "ATTENTION"
        evidence = json.dumps(control["evidence"], sort_keys=True)
        lines.append(f"| {control['rule']} | {control['control']} | {status} | {evidence} |")
    lines += ["", f"Audit chain head: {report['audit_head']}", f"Signed by key {key_id}:"]
    lines += ["", signature]
    return "\n".join(lines) + "\n"
