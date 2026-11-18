"""Training data for the router (Lab 93): questions, and the route the desk should take.

Every example is a short chat: the router's instructions, a question, and the answer in the
RouteDecision shape the graph expects (Lab 30). Questions come from templates filled with the
desk's own clients, sectors and tickers. The test templates are kept apart and include the
tricky wordings that fool the word rules, so the test shows what the model really learned.
"""

import itertools
import json
import string

from sovereign_brain.graphs.routing import ROUTER_PROMPT, Route, RouteDecision

FILLERS = {
    "client": ["C-1042", "C-2077", "C-3105"],
    "sector": ["Energy", "Financials", "Technology", "Healthcare"],
    "ticker": ["GLFP", "SNRS", "MDNB", "NOVA"],
}
OWN = "It is about the client's own holdings."
GENERAL = "It asks for general knowledge, not about one client's holdings."

TRAIN: list[tuple[Route, str, str]] = [
    ("portfolio", "What share of {client}'s portfolio is in {sector}?", OWN),
    ("portfolio", "How exposed is {client} to {sector}?", OWN),
    ("portfolio", "List the positions of {client} in {sector}.", OWN),
    ("portfolio", "How big is {client}'s stake in {ticker}?", OWN),
    ("portfolio", "Run a stress test of a 20% fall in {sector} for {client}.", OWN),
    ("portfolio", "What is the current price of {ticker} in {client}'s holdings?", OWN),
    ("portfolio", "Is {client} too heavily invested in {sector}?", OWN),
    ("general", "What does the {sector} sector usually include?", GENERAL),
    ("general", "Explain what a moderate risk profile means.", GENERAL),
    ("general", "How do rising interest rates usually affect {sector} companies?", GENERAL),
    ("general", "What is the difference between a bond and a share?", GENERAL),
    ("general", "Why do analysts watch the {sector} sector closely this year?", GENERAL),
    ("general", "What does a stress test mean in banking regulation?", GENERAL),
    ("general", "Define diversification in one sentence.", GENERAL),
    ("general", "Which risks are typical for the {sector} industry?", GENERAL),
    ("general", "How is the {sector} sector doing in the market this quarter?", GENERAL),
    ("general", "What does a {sector} analyst look at first?", GENERAL),
    ("general", "Name two well-known ratios for judging {sector} companies.", GENERAL),
    ("general", "Is {sector} considered a defensive sector?", GENERAL),
]
TEST: list[tuple[Route, str, str]] = [
    ("portfolio", "How did the oil slump hit {client}'s energy names?", OWN),
    ("portfolio", "Which of {client}'s {sector} companies would worry you most?", OWN),
    ("portfolio", "Does {client} own too much {ticker}?", OWN),
    ("general", "In general, what does sector exposure mean?", GENERAL),
    ("general", "What usually moves the price of {sector} shares?", GENERAL),
    ("general", "Explain what a portfolio stress test is, without numbers.", GENERAL),
]


def fill_all(template: str) -> list[str]:
    """Every question a template can make with the fillers it names."""
    names = [name for _, name, _, _ in string.Formatter().parse(template) if name]
    choices = [FILLERS[name] for name in names]
    combos = itertools.product(*choices)
    return [template.format(**dict(zip(names, combo, strict=True))) for combo in combos]


def example(question: str, route: Route, reason: str) -> dict:
    """One chat in the format fine-tuning tools read: system, user, assistant."""
    answer = RouteDecision(route=route, reason=reason).model_dump_json()
    return {
        "messages": [
            {"role": "system", "content": ROUTER_PROMPT},
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ]
    }


def build(templates: list[tuple[Route, str, str]]) -> list[dict]:
    return [
        example(question, route, reason)
        for route, template, reason in templates
        for question in fill_all(template)
    ]


def to_jsonl(examples: list[dict]) -> str:
    return "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in examples)
