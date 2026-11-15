"""The figure check for portfolio answers (Lab 24): every number must come from the tools."""

import re

FIGURE = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")  # 18.5, 185000, 1,000,000


def figures(text: str) -> dict[float, str]:
    """The numbers in a text, by value: "185,000" and "185000" are the same figure."""
    found = {}
    for match in FIGURE.findall(text):
        digits = match.replace(",", "")
        if len(digits.replace(".", "")) >= 2:  # single digits ("3 holdings") are not checked
            found[float(digits)] = match
    return found


def unsupported_figures(answer: str, sources: str) -> list[str]:
    """Figures in the answer that appear nowhere in the sources, as written in the answer."""
    known = figures(sources)
    return [written for value, written in figures(answer).items() if value not in known]
