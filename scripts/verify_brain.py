"""Lab 100: check the sealed record of one Brain decision, like a regulator would.

Usage: uv run python scripts/verify_brain.py <run_id> [username]   (default user: yusuf)
"""

import sys

import httpx
from auth_helper import API_URL, login, tls_verify

from sovereign_brain.security.signing import report_hash, verify


def main(run_id: str, username: str) -> None:
    headers = {"Authorization": f"Bearer {login(API_URL, username)}"}
    with httpx.Client(base_url=API_URL, headers=headers, verify=tls_verify()) as http:
        events = http.get("/v1/audit/events", params={"limit": 500}).json()
        key = http.get("/v1/approvals/signing-key").json()
        run = http.get(f"/v1/brain/runs/{run_id}").json()
    sealed = [e for e in events if e["subject"] == run_id and e["action"].startswith("brain.")]
    if not sealed:
        sys.exit(f"No sealed decision for run {run_id}")
    details = dict(sealed[-1]["details"])
    signature = details.pop("signature")
    checks = {
        "signature valid": verify(details, signature, key["public_key_pem"]),
        "draft unchanged": details["draft_sha256"] == report_hash(run["draft"]),
        "four eyes": details["decided_by"] != details["requested_by"],
    }
    for name, ok in checks.items():
        print(f"{'OK  ' if ok else 'FAIL'}  {name}")
    print(f"{details['decision']} by {details['decided_by']} (asked by {details['requested_by']})")
    sys.exit(0 if all(checks.values()) else 1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "yusuf")
