"""The Critic pattern (Lab 55): a writer drafts, a critic finds what is wrong, until it is right.

The critic works in two layers. First plain code checks the draft against fixed criteria
(length, client ID, every figure found in the notes). Only a draft that passes those is read
by the critic model, which judges the rest. Each round is written to a history, so the
whole "internal monologue" can be shown. The number of rounds is limited.
"""

import logging
import operator
import re
from typing import Annotated, Literal, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from pydantic import BaseModel, Field

from sovereign_brain.graphs.context import ResearchContext

logger = logging.getLogger("sovereign_brain.team")

WRITER_PROMPT = (
    "You write the final answer of a bank research case for the client file. Use at most three "
    "sentences, name the client ID, and use only figures that appear in the team's notes."
)
CRITIC_PROMPT = (
    "You are a strict reviewer at Crescent Ledger Bank. Check the draft against the team's notes "
    "only. Approve it if every statement is supported by the notes and it answers the question. "
    "Otherwise ask for a revision and list each problem in one short sentence."
)
FIGURE = re.compile(r"\d+(?:[.,]\d+)*")


class Critique(BaseModel):
    """The critic's judgement of one draft."""

    verdict: Literal["approve", "revise"]
    problems: list[str] = Field(default_factory=list, max_length=5)


class CriticInput(TypedDict):
    case: dict  # a CaseFile, as a dictionary (Lab 54)


class CriticOutput(TypedDict):
    draft: str
    verdict: str
    rounds: int


class CriticState(CriticInput):
    draft: str
    problems: list[str]  # overwritten: the problems of the latest draft
    verdict: str  # approve, revise, or gave_up when the rounds run out
    rounds: int
    history: Annotated[list[dict], operator.add]  # appended: the internal monologue


def figures(text: str) -> set[str]:
    """Every number in a text, without thousands separators: "185,000" -> "185000"."""
    return {match.replace(",", "") for match in FIGURE.findall(text)}


def rule_problems(draft: str, case: dict) -> list[str]:
    """The fixed criteria, checked by code: the same draft always gets the same verdict."""
    problems = []
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", draft.strip()) if s]
    if len(sentences) > 3:
        problems.append(f"Too long: {len(sentences)} sentences, at most 3.")
    if case["client_id"] not in draft:
        problems.append(f"The client ID {case['client_id']} is missing.")
    sources = case["question"] + " " + " ".join(note["text"] for note in case["notes"])
    unsupported = figures(draft.replace(case["client_id"], "")) - figures(sources)
    for figure in sorted(unsupported):
        problems.append(f"The figure {figure} is not in the notes.")
    return problems


def case_text(case: dict) -> str:
    notes = "\n".join(f"- {note['author']}: {note['text']}" for note in case["notes"])
    return f"Client {case['client_id']}. Question: {case['question']}\nTeam notes:\n{notes}"


def build_critic_graph(model: BaseChatModel) -> CompiledStateGraph:
    critic = model.with_structured_output(Critique)

    async def write(state: CriticState) -> dict:
        """The first draft from the team's answer; later drafts fix the listed problems."""
        rounds = state.get("rounds", 0) + 1
        request = f"{case_text(state['case'])}\nTeam answer: {state['case']['answer']}"
        if state.get("problems"):
            fixes = "\n".join(f"- {problem}" for problem in state["problems"])
            request += f"\nYour last draft: {state['draft']}\nFix these problems:\n{fixes}"
        reply = await model.ainvoke([SystemMessage(WRITER_PROMPT), HumanMessage(request)])
        draft = str(reply.content)
        return {
            "draft": draft,
            "rounds": rounds,
            "history": [{"step": "draft", "round": rounds, "text": draft}],
        }

    async def critique(state: CriticState) -> dict:
        """Code criteria first; the critic model only reads drafts that pass them."""
        problems, by = rule_problems(state["draft"], state["case"]), "rules"
        verdict = "revise" if problems else "approve"
        if not problems:
            by = "model"
            request = f"{case_text(state['case'])}\nDraft: {state['draft']}"
            try:
                judgement = await critic.ainvoke(
                    [SystemMessage(CRITIC_PROMPT), HumanMessage(request)]
                )
            except Exception as error:  # an unreadable critique never blocks a correct draft
                logger.warning("Critic model failed, keeping the code verdict: %r", error)
                judgement, by = None, "rules"
            if isinstance(judgement, Critique):
                verdict, problems = judgement.verdict, judgement.problems
        entry = {
            "step": "critique",
            "round": state["rounds"],
            "by": by,
            "verdict": verdict,
            "problems": problems,
        }
        return {"verdict": verdict, "problems": problems, "history": [entry]}

    def after_critique(state: CriticState, runtime: Runtime[ResearchContext]) -> str:
        if state["verdict"] == "approve":
            return "done"
        if state["rounds"] > runtime.context.max_revisions:
            return "give_up"
        return "revise"

    def give_up(state: CriticState) -> dict:
        """Out of rounds: keep the last draft, and say plainly that it was not approved."""
        return {"verdict": "gave_up"}

    builder = StateGraph(
        CriticState,
        context_schema=ResearchContext,
        input_schema=CriticInput,
        output_schema=CriticOutput,
    )
    builder.add_node("write", write)
    builder.add_node("critique", critique)
    builder.add_node("give_up", give_up)
    builder.add_edge(START, "write")
    builder.add_edge("write", "critique")
    builder.add_conditional_edges(
        "critique", after_critique, {"done": END, "revise": "write", "give_up": "give_up"}
    )
    builder.add_edge("give_up", END)
    return builder.compile(name="critic")
