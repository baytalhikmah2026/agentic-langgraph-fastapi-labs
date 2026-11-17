"""Labs 36-37: show a thread's checkpoint history, rewind it, or correct its question.

    uv run python scripts/time_travel.py amina energy-review
    uv run python scripts/time_travel.py amina energy-review --rewind <checkpoint_id>
    uv run python scripts/time_travel.py amina energy-review --correct <checkpoint_id>
        --question "Summarise this client's exposure to financial stocks."
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


def run_again(client: httpx.Client, path: str, body: dict) -> None:
    """Send a rewind or a correction, and print the new answer (or why it was refused)."""
    response = client.post(path, json=body)
    if response.is_error:
        print(f"{response.status_code}: {response.json()['message']}")
        return
    print(f"New answer: {response.json()['summary']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Thread history, time travel and corrections")
    parser.add_argument("username")
    parser.add_argument("thread_id")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--rewind", metavar="CHECKPOINT_ID")
    action.add_argument("--correct", metavar="CHECKPOINT_ID")
    parser.add_argument("--question", help="the corrected question (with --correct)")
    args = parser.parse_args()
    if args.correct and not args.question:
        parser.error("--correct needs --question")
    token = login(API, args.username)
    headers = {"Authorization": f"Bearer {token}"}
    # A rewind or a correction runs the model again, which can take a while on a laptop
    with httpx.Client(base_url=API, headers=headers, timeout=180) as client:
        threads = f"/v1/threads/{args.thread_id}"
        if args.rewind:
            run_again(client, f"{threads}/rewind", {"checkpoint_id": args.rewind})
        elif args.correct:
            body = {"checkpoint_id": args.correct, "question": args.question}
            run_again(client, f"{threads}/correct", body)
        show_history(client, args.thread_id)
