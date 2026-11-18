"""Lab 93: how often does each router choose the right route on the held-out test questions?

Usage: uv run python scripts/eval_router.py [model ...]   (default: qwen3:4b sb-router)
Models are asked through Ollama (SB_OLLAMA_BASE_URL); the word rules from Lab 23 run too.
"""

import sys

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from sovereign_brain.core.settings import get_settings
from sovereign_brain.finetune.router_data import TEST, build
from sovereign_brain.graphs.routing import ROUTER_PROMPT, RouteDecision, classify_question


def held_out() -> list[tuple[str, str]]:
    """The test questions and their right routes (never seen during training)."""
    pairs = []
    for item in build(TEST):
        _, user, assistant = item["messages"]
        decision = RouteDecision.model_validate_json(assistant["content"])
        pairs.append((user["content"], decision.route))
    return pairs


def model_accuracy(name: str, questions: list[tuple[str, str]]) -> float:
    model = ChatOllama(
        model=name, base_url=get_settings().ollama_base_url, temperature=0, reasoning=False
    ).with_structured_output(RouteDecision)
    right = 0
    for question, route in questions:
        try:
            decision = model.invoke([SystemMessage(ROUTER_PROMPT), HumanMessage(question)])
            right += decision.route == route
        except Exception:  # an answer in the wrong shape counts as a wrong route
            pass
    return right / len(questions)


def main(models: list[str]) -> None:
    questions = held_out()
    rules = sum(classify_question(question) == route for question, route in questions)
    print(f"{len(questions)} test questions")
    print(f"{'router':<14} {'right':>6}")
    print(f"{'word rules':<14} {rules / len(questions):>6.0%}")
    for name in models:
        print(f"{name:<14} {model_accuracy(name, questions):>6.0%}")


if __name__ == "__main__":
    main(sys.argv[1:] or ["qwen3:4b", "sb-router"])
