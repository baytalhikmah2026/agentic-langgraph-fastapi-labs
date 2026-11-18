"""Lab 98: start a Brain run over the live channel and print every step as it happens.

Lab 99: it signs in with its first message; the token never appears in the address.

Usage: uv run python scripts/brain_live.py [username] [client_id] [question]
Set SB_API_URL and SB_API_CA_FILE to go through the HTTPS gate (Lab 87): then it uses wss://.
"""

import asyncio
import json
import sys

from auth_helper import API_URL, login, tls_verify
from websockets.asyncio.client import connect

QUESTION = "How big is this client's energy exposure, and what are the main risks?"


async def main(username: str, request: dict) -> None:
    token = login(API_URL, username)
    url = API_URL.replace("http", "ws", 1) + "/v1/brain/ws"
    async with connect(url, ssl=tls_verify() if url.startswith("wss") else None) as socket:
        await socket.send(json.dumps({"token": token}))  # first message: sign in
        await socket.send(json.dumps(request))
        async for message in socket:
            event = json.loads(message)
            agent, data = event.get("agent") or "", json.dumps(event["data"])
            print(f"{event['at'][11:19]}  {event['type']:<16} {agent:<13} {data}")
            if event["type"] == "started":
                print(f"run {event['run_id']}")


if __name__ == "__main__":
    username = sys.argv[1] if len(sys.argv) > 1 else "amina"
    client_id = sys.argv[2] if len(sys.argv) > 2 else "C-1042"
    question = " ".join(sys.argv[3:]) or QUESTION
    asyncio.run(main(username, {"client_id": client_id, "question": question}))
