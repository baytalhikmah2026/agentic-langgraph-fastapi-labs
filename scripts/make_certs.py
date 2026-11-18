"""Lab 74: create the lab CA and the certificates for mutual TLS in ops/certs/.

Usage: uv run python scripts/make_certs.py
Run it again to replace every certificate (for example when they expire after a year).
"""

from pathlib import Path

from sovereign_brain.security.certs import issue, make_ca, save

FOLDER = Path("ops/certs")


def main() -> None:
    ca = make_ca()
    save(ca, FOLDER, "ca")
    save(issue(ca, "market", ["market", "localhost", "127.0.0.1"], client=False), FOLDER, "market")
    save(issue(ca, "sb-api", ["sb-api"], client=True), FOLDER, "api-client")
    for path in sorted(FOLDER.iterdir()):
        print(path.as_posix())


if __name__ == "__main__":
    main()
