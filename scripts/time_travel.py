"""Lab 36: show a thread's checkpoint history, and rewind it to one of its checkpoints.

    uv run python scripts/time_travel.py amina energy-review
    uv run python scripts/time_travel.py amina energy-review --rewind <checkpoint_id>
"""

import argparse

import httpx
from auth_helper import login

API = "http://127.0.0.1:8000"


def show_history(client: httpx.Client, thread_id: str) -> None:
    response = client.get(f"/v1/threads/{thread_id}/history", params={"limit": 50})
    response.raise_for_status()
    print(f"{'step':>4}  {'source':<6}  {'next':<10}  {'msgs':>4}  checkpoint_id")
    for checkpoint in response.json():
        next_stations = ",".join(checkpoint["next"]) or "-"
        print(
            f"{checkpoint['step']:>4}  {checkpoint['source']:<6}  {next_stations:<10}  "
            f"{checkpoint['messages']:>4}  {checkpoint['checkpoint_id']}"
        )


def rewind(client: httpx.Client, thread_id: str, checkpoint_id: str) -> None:
    response = client.post(
        f"/v1/threads/{thread_id}/rewind", json={"checkpoint_id": checkpoint_id}
    )
    if response.is_error:
        print(f"{response.status_code}: {response.json()['message']}")
        return
    print(f"New answer: {response.json()['summary']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Thread history and time travel")
    parser.add_argument("username")
    parser.add_argument("thread_id")
    parser.add_argument("--rewind", metavar="CHECKPOINT_ID")
    args = parser.parse_args()
    token = login(API, args.username)
    headers = {"Authorization": f"Bearer {token}"}
    # A rewind runs the model again, which can take a while on a laptop
    with httpx.Client(base_url=API, headers=headers, timeout=180) as client:
        if args.rewind:
            rewind(client, args.thread_id, args.rewind)
        show_history(client, args.thread_id)
