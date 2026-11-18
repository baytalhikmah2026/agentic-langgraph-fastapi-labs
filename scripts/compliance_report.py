"""Lab 95: fetch the signed compliance report, check its seal, save it as Markdown.

Usage: uv run python scripts/compliance_report.py [username] [days]   (default: yusuf 30)
"""

import sys
from datetime import date
from pathlib import Path

import httpx
from auth_helper import API_URL, login, tls_verify

from sovereign_brain.security.signing import verify


def main(username: str, days: int) -> None:
    headers = {"Authorization": f"Bearer {login(API_URL, username)}"}
    with httpx.Client(base_url=API_URL, headers=headers, verify=tls_verify()) as http:
        sealed = http.get("/v1/compliance/report", params={"days": days}).json()
        page = http.get("/v1/compliance/report.md", params={"days": days}).text
        key = http.get("/v1/approvals/signing-key").json()
    if not verify(sealed["report"], sealed["signature"], key["public_key_pem"]):
        sys.exit("The report's signature is NOT valid.")
    path = Path("reports") / f"compliance-{date.today().isoformat()}.md"
    path.parent.mkdir(exist_ok=True)
    path.write_text(page, encoding="utf-8")
    for control in sealed["report"]["controls"]:
        print(f"{'met      ' if control['met'] else 'ATTENTION'}  {control['rule']}")
    print(f"Signature valid (key {key['key_id']}). Saved to {path.as_posix()}")


if __name__ == "__main__":
    username = sys.argv[1] if len(sys.argv) > 1 else "yusuf"
    main(username, int(sys.argv[2]) if len(sys.argv) > 2 else 30)
