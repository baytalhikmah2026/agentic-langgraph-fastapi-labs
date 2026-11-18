"""Lab 76: check the signature of a decided report, the way an auditor would.

Usage: uv run python scripts/verify_approval.py <approval_id> [username]
"""

import sys

import httpx
from auth_helper import login

from sovereign_brain.security.signing import report_hash, verify

API = "http://127.0.0.1:8000"


def main(approval_id: str, username: str) -> None:
    headers = {"Authorization": f"Bearer {login(API, username)}"}
    signed = httpx.get(f"{API}/v1/approvals/{approval_id}/signature", headers=headers).json()
    key = httpx.get(f"{API}/v1/approvals/signing-key", headers=headers).json()
    history = httpx.get(f"{API}/v1/approvals/{approval_id}/history", headers=headers).json()
    statement = signed["statement"]
    checks = {
        "signed with the desk's current key": statement["key_id"] == key["key_id"],
        "signature matches the statement": verify(
            statement, signed["signature"], key["public_key_pem"]
        ),
        "report unchanged since the decision": statement["report_sha256"]
        == report_hash(history["approval"]["report"] or {}),
    }
    print(f"{statement['decision']} by {statement['decided_by']} at {statement['decided_at']}")
    for check, passed in checks.items():
        print(f"  {'OK    ' if passed else 'FAILED'}  {check}")
    print("VALID" if all(checks.values()) else "NOT VALID")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "yusuf")
