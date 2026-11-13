"""Lab 11: send three research requests and three health checks at the same time."""

import asyncio
import json
import time
from pathlib import Path

import httpx

API = "http://127.0.0.1:8000"
PAYLOAD = json.loads(Path("requests/research_ok.json").read_text(encoding="utf-8"))


async def timed(client: httpx.AsyncClient, name: str, method: str, path: str) -> None:
    start = time.perf_counter()
    if method == "POST":
        response = await client.post(f"{API}{path}", json=PAYLOAD)
    else:
        response = await client.get(f"{API}{path}")
    seconds = time.perf_counter() - start
    print(f"{seconds:6.2f}s  {name:<11} {response.status_code}")


async def main() -> None:
    async with httpx.AsyncClient(timeout=300) as client:
        start = time.perf_counter()
        await asyncio.gather(
            *(timed(client, f"research {n}", "POST", "/v1/research") for n in (1, 2, 3)),
            *(timed(client, f"health {n}", "GET", "/health") for n in (1, 2, 3)),
        )
        print(f"{time.perf_counter() - start:6.2f}s  all done")


if __name__ == "__main__":
    asyncio.run(main())
