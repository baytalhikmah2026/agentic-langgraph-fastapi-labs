"""Lab 80: fetch the signed security report, check its signature, save it as Markdown.

Usage: uv run python scripts/security_report.py [username]   (a lead or an auditor)
"""

import sys
from datetime import date
from pathlib import Path

import httpx
from auth_helper import login

from sovereign_brain.security.signing import verify

API = "http://127.0.0.1:8000"


def main(username: str) -> None:
    headers = {"Authorization": f"Bearer {login(API, username)}"}
    report = httpx.get(f"{API}/v1/security/report", headers=headers).json()
    key = httpx.get(f"{API}/v1/approvals/signing-key", headers=headers).json()
    posture = report["posture"]
    signed = verify(posture, report["signature"], key["public_key_pem"])
    chain = posture["audit_chain"]
    lines = [
        f"# Security report, {posture['generated_at']}",
        "",
        "| Layer | State |",
        "|---|---|",
        f"| Injection guard (Lab 71) | {len(posture['injection_guard_rules'])} rules |",
        f"| PII masking (Lab 72) | {'on' if posture['pii_masking'] else 'OFF'} |",
        f"| Roles (Lab 73) | {len(posture['permissions'])} permissions |",
        f"| Market mutual TLS (Lab 74) | {'on' if posture['market_mutual_tls'] else 'OFF'} |",
        f"| Secrets from Vault (Lab 75) | {'yes' if posture['secrets_from_vault'] else 'NO'} |",
        f"| Signing key (Lab 76) | {posture['signing_key_id']} |",
        f"| Audit chain (Lab 77) | {chain['events']} entries, "
        f"{'intact' if chain['valid'] else 'TAMPERED'} |",
        "",
        f"Signature: {'valid' if signed else 'NOT VALID'} (key {key['key_id']})",
    ]
    path = Path("reports") / f"security-{date.today().isoformat()}.md"
    path.parent.mkdir(exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"Saved to {path.as_posix()}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "yusuf")
