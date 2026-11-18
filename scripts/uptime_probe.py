"""Lab 90: knock on the gate again and again, and count every answer that wasn't a success.

Usage: uv run python scripts/uptime_probe.py [seconds]   (default 240)
Set SB_API_URL and SB_API_CA_FILE first to go through the HTTPS gate (Lab 87).
Exit code 0 when every request succeeded, 1 otherwise.
"""

import sys
import time
from collections import Counter

import httpx
from auth_helper import API_URL, tls_verify

INTERVAL_SECONDS = 0.2  # about five knocks per second


def main(seconds: float) -> None:
    outcomes: Counter[str] = Counter()
    slowest = 0.0
    stop_at = time.monotonic() + seconds
    print(f"Knocking on {API_URL}/health/ready for {seconds:.0f} seconds ...")
    with httpx.Client(base_url=API_URL, verify=tls_verify(), timeout=5) as client:
        while time.monotonic() < stop_at:
            started = time.monotonic()
            try:
                outcome = str(client.get("/health/ready").status_code)
            except httpx.HTTPError as error:  # no answer at all counts as a failure too
                outcome = type(error).__name__
            outcomes[outcome] += 1
            slowest = max(slowest, time.monotonic() - started)
            time.sleep(INTERVAL_SECONDS)
    total = sum(outcomes.values())
    failed = total - outcomes["200"]
    print(f"{total} requests, {failed} failed, slowest {slowest * 1000:.0f} ms")
    for outcome, count in sorted(outcomes.items()):
        print(f"  {outcome}: {count}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 240)
