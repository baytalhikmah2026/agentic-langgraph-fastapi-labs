"""The worker's heartbeat (Lab 86): fresh while it beats, stale when it stops."""

from pathlib import Path

from sovereign_brain.workers.heartbeat import MAX_AGE_SECONDS, is_fresh


def test_the_heartbeat_goes_stale_when_the_worker_stops(tmp_path: Path) -> None:
    heartbeat = tmp_path / "research-worker.alive"
    assert not is_fresh(heartbeat)  # no file yet: the worker never started

    heartbeat.touch()
    touched = heartbeat.stat().st_mtime

    assert is_fresh(heartbeat, now=touched + 5)
    assert not is_fresh(heartbeat, now=touched + MAX_AGE_SECONDS + 1)
