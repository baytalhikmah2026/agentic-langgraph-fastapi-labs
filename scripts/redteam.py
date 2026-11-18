"""Lab 79: run the red-team suite against the running desk and print a report.

Usage: uv run python scripts/redteam.py
It asks for the passwords of amina, omar, layla and yusuf, requests one report as amina (to
have something to attack), then runs every attack. Exit code 1 if any defence failed.
"""

import sys

import httpx
from auth_helper import login

from sovereign_brain.security.redteam import build_attacks, run_attacks

API = "http://127.0.0.1:8000"


def main() -> int:
    tokens = {user: login(API, user) for user in ("amina", "omar", "layla", "yusuf")}
    with httpx.Client(base_url=API, timeout=120.0) as http:
        started = http.post(
            "/v1/approvals/reports/C-1042", headers={"Authorization": f"Bearer {tokens['amina']}"}
        )
        started.raise_for_status()
        results = run_attacks(http, build_attacks(tokens, started.json()["approval_id"]))
    print(f"{'RESULT':<8} {'CATEGORY':<22} {'ATTACK':<42} STATUS")
    for result in results:
        verdict = "DEFENDED" if result.passed else "OPEN"
        print(f"{verdict:<8} {result.attack.category:<22} {result.attack.name:<42} {result.status}")
    opened = [r for r in results if not r.passed]
    print(f"{len(results) - len(opened)} of {len(results)} attacks defended")
    return 1 if opened else 0


if __name__ == "__main__":
    sys.exit(main())
