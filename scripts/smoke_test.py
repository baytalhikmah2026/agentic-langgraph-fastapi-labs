"""Lab 10: end-to-end smoke test of the running stack (API + Ollama + model)."""

import json
import sys
from pathlib import Path

import httpx

from sovereign_brain.core.settings import get_settings

API = "http://127.0.0.1:8000"
OLLAMA = "http://127.0.0.1:11434"
REQUEST_FILE = Path("requests/research_ok.json")


def check(name: str, ok: bool, detail: str) -> bool:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    return ok


def run_checks(client: httpx.Client) -> list[bool]:
    results = []
    health = client.get(f"{API}/health")
    results.append(check("API health", health.status_code == 200, health.text))

    required = {get_settings().llm_model, "nomic-embed-text:v1.5"}
    models = {model["name"] for model in client.get(f"{OLLAMA}/api/tags").json()["models"]}
    missing = required - models
    detail = f"missing {', '.join(sorted(missing))}" if missing else ", ".join(sorted(required))
    results.append(check("Ollama models", not missing, detail))

    payload = json.loads(REQUEST_FILE.read_text(encoding="utf-8"))
    research = client.post(f"{API}/v1/research", json=payload)
    is_json = research.headers.get("content-type", "").startswith("application/json")
    body = research.json() if is_json else {"detail": research.text}
    completed = body.get("status") == "completed" and bool(body.get("summary"))
    ok = research.status_code == 200 and completed
    detail = f"{research.status_code} {body.get('summary', body)}"
    results.append(check("Research request", ok, detail))
    return results


def main() -> int:
    try:
        with httpx.Client(timeout=180) as client:
            results = run_checks(client)
    except httpx.HTTPError as error:
        print(f"[FAIL] Connection: {error!r}. Is the stack running? (docker compose up -d)")
        return 1
    print(f"\n{sum(results)} of {len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
