"""The newsroom's shared state (Module 6): what every agent on the team can read and add to."""

import operator
from typing import Annotated, TypedDict

from sovereign_brain.graphs.trail import TrailEntry


class WorkNote(TypedDict):
    """One contribution to the team's notebook: who wrote it, and what."""

    author: str
    text: str


class TeamInput(TypedDict):
    client_id: str
    client_profile: str
    question: str


class TeamOutput(TypedDict):
    answer: str
    notes: list[WorkNote]


class TeamState(TeamInput):
    notes: Annotated[list[WorkNote], operator.add]  # appended: the team's shared notebook
    next: str  # overwritten: who works next (chosen by the supervisor)
    task: str  # overwritten: what that worker was asked to do
    turns: int  # overwritten: how many times the supervisor has decided
    answer: str  # overwritten: the final answer, once the writer has written it
    trail: Annotated[list[TrailEntry], operator.add]  # appended: who did what (Lab 26)


def team_brief(state: TeamState) -> str:
    """What every team member reads: the client, the question and the notes so far."""
    lines = [f"Client {state['client_id']} ({state['client_profile']}): {state['question']}"]
    notes = state.get("notes") or []
    if notes:
        lines.append("Team notes so far:")
        lines += [f"- {note['author']}: {note['text']}" for note in notes]
    if state.get("answer"):
        lines.append(f"Answer written: {state['answer']}")
    return "\n".join(lines)
