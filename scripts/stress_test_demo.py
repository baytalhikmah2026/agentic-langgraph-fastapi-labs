"""Lab 41: show the stress-test form the model will see, then fill it in twice.

Run with: uv run python scripts/stress_test_demo.py
No model and no database are needed: the calculator is plain Python.
"""

import json

from pydantic import ValidationError

from sovereign_brain.tools.risk import stress_test_tool

GOOD = {
    "client_id": "C-1042",
    "sector": "Energy",
    "sector_value_usd": 185000,
    "portfolio_value_usd": 1000000,
    "shock_percent": 40,
    "risk_profile": "moderate",
}
# What a confused model might send: a typo in the ID, an impossible fall, an invented field
BAD = {**GOOD, "client_id": "1042", "shock_percent": 120, "currency": "EUR"}

print(f"Tool: {stress_test_tool.name}")
print(f"Description: {stress_test_tool.description}")
print("Fields the model fills in:")
print(json.dumps(stress_test_tool.args, indent=2))

print("\nA correct request:")
print(json.dumps(stress_test_tool.invoke(GOOD), indent=2))

print("\nA malformed request:")
try:
    stress_test_tool.invoke(BAD)
except ValidationError as error:
    for problem in error.errors():
        print(f"- {problem['loc'][0]}: {problem['msg']}")
