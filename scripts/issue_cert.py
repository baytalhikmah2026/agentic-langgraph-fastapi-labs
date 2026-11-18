"""Lab 87: issue one more server certificate from the existing lab CA (ops/certs/ca.*).

Usage: uv run python scripts/issue_cert.py <name> <host> [more hosts ...]
Example: uv run python scripts/issue_cert.py desk localhost desk.localhost
Unlike make_certs.py, this keeps the CA, so every certificate issued before stays valid.
"""

import sys
from pathlib import Path

from sovereign_brain.security.certs import issue, load, save

FOLDER = Path("ops/certs")


def main(name: str, hosts: list[str]) -> None:
    ca = load(FOLDER, "ca")
    save(issue(ca, hosts[0], hosts, client=False), FOLDER, name)
    print(f"Issued {FOLDER.as_posix()}/{name}.crt for {', '.join(hosts)}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2:])
