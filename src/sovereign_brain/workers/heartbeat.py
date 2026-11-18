"""The research worker's heartbeat (Lab 86): a file it touches every few seconds.

A worker has no web port to ask "are you alive?", so it leaves a sign of life instead.
Kubernetes runs  python -m sovereign_brain.workers.heartbeat  as its liveness probe:
exit code 0 while the file is fresh, 1 when the worker has frozen or stopped.
This module stays small on purpose: the probe runs it every 15 seconds.
"""

import asyncio
import sys
import tempfile
import time
from pathlib import Path

HEARTBEAT = Path(tempfile.gettempdir()) / "research-worker.alive"
BEAT_EVERY_SECONDS = 10
MAX_AGE_SECONDS = 60


async def beat(path: Path = HEARTBEAT) -> None:
    """Touch the file while the event loop runs; a stuck loop stops the beat."""
    while True:
        path.touch()
        await asyncio.sleep(BEAT_EVERY_SECONDS)


def is_fresh(path: Path = HEARTBEAT, now: float | None = None) -> bool:
    try:
        age = (now if now is not None else time.time()) - path.stat().st_mtime
    except FileNotFoundError:
        return False
    return age < MAX_AGE_SECONDS


if __name__ == "__main__":
    sys.exit(0 if is_fresh() else 1)
