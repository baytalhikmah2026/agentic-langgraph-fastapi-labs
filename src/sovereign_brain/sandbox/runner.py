"""The sandbox runner (Lab 47): runs one short Python snippet in a fresh, limited process.

It lives in its own container (Compose service `sandbox`): no network, a read-only disk, no
Linux capabilities, tight memory, CPU and process limits, and gVisor on Linux if installed.
Each run gets an empty temporary folder that is deleted afterwards, so nothing survives from
one run to the next.

Run it on its own with: uv run fastapi dev src/sovereign_brain/sandbox/runner.py --port 8200
"""

import asyncio
import math
import os
import sys
import tempfile

from fastapi import FastAPI
from pydantic import BaseModel, Field

TIMEOUT_SECONDS = float(os.environ.get("SB_SANDBOX_TIMEOUT", "5"))
OUTPUT_LIMIT = 4000  # characters of stdout and stderr returned, at most
MEMORY_BYTES = 256 * 1024 * 1024


class RunRequest(BaseModel):
    code: str = Field(min_length=1, max_length=4000)


class RunResult(BaseModel):
    stdout: str
    stderr: str
    exit_code: int | None
    timed_out: bool


def set_limits() -> None:
    """Runs in the new process just before the snippet starts (Linux): hard resource limits."""
    import resource  # Linux and macOS only, so imported here

    cpu = max(1, math.ceil(TIMEOUT_SECONDS))
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))  # seconds of CPU time
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_BYTES, MEMORY_BYTES))  # memory
    resource.setrlimit(resource.RLIMIT_FSIZE, (1_000_000, 1_000_000))  # size of any file written


def child_environment(workdir: str) -> dict[str, str]:
    """A nearly empty environment: no secrets, no settings, home in the throwaway folder."""
    env = {"HOME": workdir, "LANG": "C.UTF-8"}
    if "SYSTEMROOT" in os.environ:  # Windows needs this one to start Python at all
        env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
    return env


async def run_snippet(code: str) -> RunResult:
    """Run the code with `python -I` in an empty folder; stop it after TIMEOUT_SECONDS."""
    with tempfile.TemporaryDirectory(prefix="run-") as workdir:
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-I",  # isolated mode: ignores environment variables and the user's site folder
            "-c",
            code,
            cwd=workdir,
            env=child_environment(workdir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            preexec_fn=set_limits if sys.platform == "linux" else None,
        )
        try:
            out, err = await asyncio.wait_for(process.communicate(), TIMEOUT_SECONDS)
            timed_out = False
        except TimeoutError:
            process.kill()
            out, err = await process.communicate()
            timed_out = True
    # Leaving the "with" block deleted the folder and everything the snippet wrote
    return RunResult(
        stdout=out.decode(errors="replace")[:OUTPUT_LIMIT],
        stderr=err.decode(errors="replace")[:OUTPUT_LIMIT],
        exit_code=process.returncode,
        timed_out=timed_out,
    )


app = FastAPI(title="Sovereign Brain sandbox runner")


@app.post("/run")
async def run(body: RunRequest) -> RunResult:
    return await run_snippet(body.code)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
