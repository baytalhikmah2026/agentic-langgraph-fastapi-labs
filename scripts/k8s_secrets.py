"""Lab 84: create the desk's Kubernetes Secrets from fresh random values and ops/certs.

Usage: uv run python scripts/k8s_secrets.py [--namespace sovereign-brain]

The Secrets go straight to the cluster through kubectl; nothing secret is written to disk or
to Git. Running it again replaces every value (sign in again, and recreate PostgreSQL's data).
"""

import argparse
import json
import secrets
import subprocess
import sys
from pathlib import Path

from sovereign_brain.security.signing import new_signing_key_pem

CERTS = Path("ops/certs")  # made by scripts/make_certs.py (Lab 74)
CERT_FILES = ["ca.crt", "market.crt", "market.key", "api-client.crt", "api-client.key"]


def secret(name: str, namespace: str, values: dict[str, str]) -> dict:
    """A Kubernetes Secret; kubectl turns stringData into base64 data for us."""
    return {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {
            "name": name,
            "namespace": namespace,
            "labels": {"app.kubernetes.io/part-of": "sovereign-brain"},
        },
        "type": "Opaque",
        "stringData": values,
    }


def apply(manifest: dict) -> None:
    """Send one object to the cluster through kubectl's standard input."""
    subprocess.run(
        ["kubectl", "apply", "-f", "-"], input=json.dumps(manifest), text=True, check=True
    )


def main(namespace: str) -> None:
    missing = [name for name in CERT_FILES if not (CERTS / name).is_file()]
    if missing:
        sys.exit(f"Missing certificates in {CERTS}: {', '.join(missing)}. Run make_certs.py.")
    password = secrets.token_urlsafe(24)
    apply(secret("postgres-credentials", namespace, {"POSTGRES_PASSWORD": password}))
    desk = {
        "SB_DATABASE_URL": f"postgresql+psycopg://sb:{password}@postgres:5432/sovereign_brain",
        "SB_JWT_SECRET": secrets.token_urlsafe(48),
        "SB_MARKET_API_TOKEN": secrets.token_urlsafe(32),
        "SB_ALERT_WEBHOOK_TOKEN": secrets.token_urlsafe(32),
        "SB_APPROVAL_SIGNING_KEY": new_signing_key_pem(),
    }
    apply(secret("desk-secrets", namespace, desk))
    certs = {name: (CERTS / name).read_text(encoding="utf-8") for name in CERT_FILES}
    apply(secret("market-tls", namespace, certs))
    print(f"Secrets saved in {namespace}: postgres-credentials, desk-secrets, market-tls")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create the desk's Kubernetes Secrets.")
    parser.add_argument("--namespace", default="sovereign-brain")
    main(parser.parse_args().namespace)
