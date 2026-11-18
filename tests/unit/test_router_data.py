"""The router's training data (Lab 93): valid answers, two separate sets, a fair test."""

import json

from sovereign_brain.finetune.router_data import TEST, TRAIN, build, to_jsonl
from sovereign_brain.graphs.routing import RouteDecision, classify_question


def questions_and_routes(examples: list[dict]) -> list[tuple[str, str]]:
    pairs = []
    for item in examples:
        _, user, assistant = item["messages"]
        decision = RouteDecision.model_validate_json(assistant["content"])  # the graph's shape
        pairs.append((user["content"], decision.route))
    return pairs


def test_train_and_test_are_valid_and_separate() -> None:
    train, test = questions_and_routes(build(TRAIN)), questions_and_routes(build(TEST))

    assert (len(train), len(test)) == (120, 33)
    assert {route for _, route in train} == {route for _, route in test} == {"portfolio", "general"}
    assert not {question for question, _ in train} & {question for question, _ in test}
    assert len(to_jsonl(build(TEST)).splitlines()) == 33
    assert json.loads(to_jsonl(build(TEST)).splitlines()[0])["messages"][0]["role"] == "system"


def test_the_test_set_holds_wordings_that_fool_the_word_rules() -> None:
    test = questions_and_routes(build(TEST))
    rules_right = sum(classify_question(question) == route for question, route in test)

    assert rules_right / len(test) < 0.5  # the model has to understand, not match words
