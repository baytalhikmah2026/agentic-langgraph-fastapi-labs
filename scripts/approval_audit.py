"""Lab 70: print the audit record of one report as a readable timeline.

Usage: uv run python scripts/approval_audit.py <approval_id> [username]
"""

import sys

import httpx
from auth_helper import login

API = "http://127.0.0.1:8000"


def main(approval_id: str, username: str) -> None:
    token = login(API, username)
    response = httpx.get(
        f"{API}/v1/approvals/{approval_id}/history",
        headers={"Authorization": f"Bearer {token}"},
    )
    response.raise_for_status()
    record = response.json()
    approval, register = record["approval"], record["register"]
    print(f"Report {approval_id} for {approval['client_id']}: {approval['status']}")
    if register:
        print(f"  requested by {register['requested_by']} at {register['requested_at']}")
        if register["decided_by"]:
            comment = register["comment"] or "no comment"
            print(f"  {register['status']} by {register['decided_by']} ({comment})")
    if approval["overridden_by"]:
        print(f"  changed by desk lead {approval['overridden_by']}")
    print("Steps:")
    for step in record["steps"]:
        who = step["actor"] or "-"
        trace = step["trace_id"] or "no trace"
        waits = ", ".join(step["next"]) or "finished"
        print(f"  {step['step']:>3}  {step['source']:<6}  by {who:<8}  next: {waits:<10}  {trace}")
    print("Trail:")
    for entry in approval["trail"]:
        print(f"  {entry['at']}  {entry['node']:<9} {entry['note']}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "amina")
