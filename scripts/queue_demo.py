"""Lab 83: queue research jobs for two analysts and watch the workers finish them.

Usage: uv run python scripts/queue_demo.py   (with the API reachable on port 8000)
"""

import time

import httpx
from auth_helper import login

API = "http://127.0.0.1:8000"
REQUEST = {"client_id": "C-1042", "question": "Summarise the exposure to energy stocks."}
JOBS_PER_ANALYST = 4  # below the rate limit of 5 model calls per minute (Lab 17)


def main() -> None:
    headers = {name: {"Authorization": f"Bearer {login(API, name)}"} for name in ("amina", "omar")}
    jobs = []
    for name, auth in headers.items():
        for _ in range(JOBS_PER_ANALYST):
            answer = httpx.post(f"{API}/v1/research/jobs", json=REQUEST, headers=auth).json()
            jobs.append((name, answer["job_id"]))
    print(f"{len(jobs)} jobs queued")
    started = time.monotonic()
    while True:
        states = [
            httpx.get(f"{API}/v1/research/jobs/{job_id}", headers=headers[name]).json()["status"]
            for name, job_id in jobs
        ]
        done = states.count("completed") + states.count("failed")
        print(
            f"{time.monotonic() - started:4.0f} s   queued {states.count('queued')}"
            f"   running {states.count('running')}   done {done}"
        )
        if done == len(jobs):
            break
        time.sleep(10)


if __name__ == "__main__":
    main()
