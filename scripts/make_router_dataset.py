"""Lab 93: write the router's training and test data to edge/finetune/data/.

Usage: uv run python scripts/make_router_dataset.py
"""

from pathlib import Path

from sovereign_brain.finetune.router_data import TEST, TRAIN, build, to_jsonl

FOLDER = Path("edge/finetune/data")


def main() -> None:
    FOLDER.mkdir(parents=True, exist_ok=True)
    for name, templates in (("router_train.jsonl", TRAIN), ("router_test.jsonl", TEST)):
        examples = build(templates)
        (FOLDER / name).write_text(to_jsonl(examples), encoding="utf-8", newline="\n")
        print(f"{FOLDER.as_posix()}/{name}: {len(examples)} examples, {len(templates)} templates")


if __name__ == "__main__":
    main()
