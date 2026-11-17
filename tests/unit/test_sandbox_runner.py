"""The sandbox runner (Lab 47): a fresh process and an empty folder for every run."""

import pytest

from sovereign_brain.sandbox import runner
from sovereign_brain.sandbox.runner import run_snippet


async def test_a_snippet_runs_and_its_output_comes_back() -> None:
    result = await run_snippet("print(6 * 7)")

    assert result.stdout.strip() == "42"
    assert result.exit_code == 0
    assert result.timed_out is False


async def test_an_endless_loop_is_stopped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "TIMEOUT_SECONDS", 0.5)

    result = await run_snippet("while True:\n    pass")

    assert result.timed_out is True


async def test_nothing_survives_from_one_run_to_the_next() -> None:
    await run_snippet("with open('left-behind.txt', 'w') as f:\n    f.write('secret')")

    result = await run_snippet("import os\nprint(os.listdir('.'))")

    assert result.stdout.strip() == "[]"
