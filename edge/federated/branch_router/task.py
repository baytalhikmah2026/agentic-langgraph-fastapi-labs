"""The shared lesson (Lab 94): a tiny router model and each branch's own, private questions.

The model is a logistic regression over word counts: it answers 1 for "portfolio" and 0 for
"general". Every branch only ever sees its own questions; only the model's numbers travel.
"""

import re

import numpy as np

VOCABULARY = [
    "portfolio", "holdings", "holding", "hold", "exposed", "exposure", "stake", "position",
    "positions", "client", "our", "their", "own", "names", "book", "family", "office",
    "what", "explain", "define", "general", "usually", "mean", "means", "typical", "market",
]
NORTH = [  # the North branch: retail clients, short questions
    ("How exposed is the client to energy?", 1),
    ("What is the client's stake in GLFP?", 1),
    ("List the positions in our client's book.", 1),
    ("Is the client's portfolio too heavy in tech?", 1),
    ("What does diversification mean?", 0),
    ("Explain what a bond is.", 0),
    ("What usually moves oil prices?", 0),
    ("Define a defensive sector.", 0),
]
SOUTH = [  # the South branch: private banking, longer wordings
    ("Which of their holdings would suffer most in a downturn?", 1),
    ("How big is their own position in Medina Bank?", 1),
    ("Summarise the exposure of this family office to energy names.", 1),
    ("Does the client hold too much of one stock?", 1),
    ("In general, what does sector exposure mean?", 0),
    ("What are typical risks in the healthcare market?", 0),
    ("Explain a stress test in simple words.", 0),
    ("What does a moderate risk profile usually mean?", 0),
]
BRANCHES = [NORTH, SOUTH]


def features(question: str) -> np.ndarray:
    words = re.findall(r"[a-z]+", question.lower())
    return np.array([words.count(word) for word in VOCABULARY], dtype=np.float64)


def branch_data(partition_id: int) -> tuple[np.ndarray, np.ndarray]:
    """The questions of one branch only: they never leave its SuperNode."""
    rows = BRANCHES[partition_id]
    return np.stack([features(q) for q, _ in rows]), np.array([label for _, label in rows])


def initial_weights() -> list[np.ndarray]:
    return [np.zeros(len(VOCABULARY)), np.zeros(1)]


def predict(weights: list[np.ndarray], x: np.ndarray) -> np.ndarray:
    w, b = weights
    return 1 / (1 + np.exp(-(x @ w + b[0])))


def train(
    weights: list[np.ndarray], x: np.ndarray, y: np.ndarray, epochs: int, lr: float
) -> list[np.ndarray]:
    """Plain gradient descent on the branch's own questions; returns new weights."""
    w, b = weights[0].copy(), weights[1].copy()
    for _ in range(epochs):
        error = predict([w, b], x) - y
        w -= lr * x.T @ error / len(y)
        b -= lr * np.array([error.mean()])
    return [w, b]


def accuracy(weights: list[np.ndarray], x: np.ndarray, y: np.ndarray) -> float:
    return float(((predict(weights, x) > 0.5) == y).mean())
