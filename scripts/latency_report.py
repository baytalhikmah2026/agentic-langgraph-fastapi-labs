"""Lab 20: read Locust's CSV results and compare each endpoint with its latency budget."""

import csv
import sys
from pathlib import Path

# The slowest 5 % of requests (p95) must be faster than these budgets, in milliseconds
BUDGETS_MS = {
    "GET /health": 50,
    "GET /v1/clients/[id]": 200,
    "POST /v1/research (cached)": 300,
    "POST /v1/auth/token": 1500,
}


def number(value: str) -> float:
    return float(value) if value not in ("", "N/A") else 0.0


def main(stats_file: Path) -> int:
    rows = list(csv.DictReader(stats_file.open(encoding="utf-8")))
    print(
        f"{'Endpoint':<28}{'Requests':>9}{'Failed':>8}{'p50':>7}{'p95':>7}{'p99':>7}"
        f"{'Budget':>8}  Result"
    )
    all_ok = True
    for row in rows:
        name = f"{row['Type']} {row['Name']}".strip()  # for example "GET /health"
        p95 = number(row["95%"])
        budget = BUDGETS_MS.get(name)
        failed = int(row["Failure Count"])
        if budget is None:
            result, budget_text = "", ""
        else:
            ok = p95 <= budget and failed == 0
            all_ok = all_ok and ok
            result, budget_text = ("OK" if ok else "OVER"), str(budget)
        print(
            f"{name:<28}{row['Request Count']:>9}{failed:>8}{number(row['50%']):>7.0f}"
            f"{p95:>7.0f}{number(row['99%']):>7.0f}{budget_text:>8}  {result}"
        )
    print("\nAll budgets met." if all_ok else "\nSome endpoints are over budget or failed.")
    return 0 if all_ok else 1


if __name__ == "__main__":
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "reports/lab20_stats.csv")
    if not path.is_file():
        sys.exit(f"{path} not found: run the Locust test with --csv reports/lab20 first.")
    sys.exit(main(path))
