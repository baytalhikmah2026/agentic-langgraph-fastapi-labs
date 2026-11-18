"""Lab 91: copy every image of ops/airgap/images.txt into the bank's own registry.

Usage: uv run python scripts/airgap_bundle.py   (with the registry from Lab 91 on localhost:5001)

Run it on the connected side, before the doors close. Our own image must already be built;
the others are pulled from their public registries once, then never again.
"""

import subprocess
import sys
from pathlib import Path

import httpx

REGISTRY = "localhost:5001"
IMAGES = Path("ops/airgap/images.txt")


def docker(*args: str) -> None:
    subprocess.run(["docker", *args], check=True, stdout=subprocess.DEVNULL)


def images() -> list[str]:
    lines = IMAGES.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def main() -> None:
    for image in images():
        if not image.startswith("sovereign-brain-api:"):  # ours is built, not pulled
            docker("pull", image)
        docker("tag", image, f"{REGISTRY}/{image}")
        docker("push", f"{REGISTRY}/{image}")
        print(f"copied  {image}  ->  {REGISTRY}/{image}")
    catalog = httpx.get(f"http://{REGISTRY}/v2/_catalog").json()["repositories"]
    missing = [image for image in images() if image.split(":")[0] not in catalog]
    if missing:
        sys.exit(f"Not in the registry: {', '.join(missing)}")
    print(f"The registry holds {len(catalog)} repositories: {', '.join(sorted(catalog))}")


if __name__ == "__main__":
    main()
