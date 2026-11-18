"""Lab 97: write the Brain's contracts as JSON Schema to docs/brain_schemas.json.

Usage: uv run python scripts/export_brain_schemas.py
Run it after every change to capstone/schemas.py; a test fails while the file is out of date.
"""

import json
from pathlib import Path

from sovereign_brain.capstone.schemas import SCHEMAS

TARGET = Path("docs/brain_schemas.json")


def document() -> str:
    schemas = {name: model.model_json_schema() for name, model in SCHEMAS.items()}
    return json.dumps(schemas, indent=2, sort_keys=True) + "\n"


if __name__ == "__main__":
    TARGET.write_text(document(), encoding="utf-8", newline="\n")
    print(f"Wrote {TARGET.as_posix()} ({len(SCHEMAS)} schemas: {', '.join(SCHEMAS)})")
