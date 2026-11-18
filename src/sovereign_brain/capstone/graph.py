"""The Sovereign Enterprise Brain (Lab 98): a supervisor and three specialists, one graph.

    supervisor ─► extraction ─► supervisor ─► sanitization ─► supervisor ─► analysis
        ▲                                                                   │
        └──────── (a figure the facts don't back: one more try) ◄──────────┘
    supervisor ─finish─► approval (pause for a person, Lab 62) ─► END

Every hand-over is one of the Lab 97 contracts. The supervisor keeps the order of trust:
facts first, then cleaning, then writing, and nothing reaches a client without a person.
The state lives in the checkpointer (PostgreSQL in the cluster), so any API pod can continue
a run that another pod started.
"""

import json
import operator
from dataclasses import dataclass, field
from typing import Annotated, Any, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from langgraph.types import interrupt

from sovereign_brain.capstone.schemas import (
    AnalysisDraft,
    BrainRequest,
    ExtractedFacts,
    Holding,
    SanitizedFacts,
    SupervisorDecision,
    unsupported_figures,
)
from sovereign_brain.security.injection import injection_rules
from sovereign_brain.security.pii import get_masker
from sovereign_brain.services.portfolio import PortfolioService

ANALYST_PROMPT = (
    "You are the analysis specialist of Crescent Ledger Bank's research desk. Write a short "
    "brief that answers the analyst's question using ONLY the facts given. Every figure you "
    "report must be an amount from the facts (a holding, a sector total, a price or the "
    "portfolio total) in USD, or a percentage. Name the main risks. Personal data appears as "
    "placeholders like <PERSON_1>; keep them as they are."
)


@dataclass(frozen=True)
class BrainContext:
    """What every run brings along: the services, the analyst, and a few limits."""

    portfolio: PortfolioService
    analyst: str
    tools: dict[str, BaseTool] = field(default_factory=dict)  # MCP tools by name (Lab 44)
    max_analysis_tries: int = 2
    max_notes: int = 3


class BrainState(TypedDict, total=False):
    request: dict  # BrainRequest
    requested_by: str  # the analyst who started the run (four eyes at the pause)
    facts: dict  # ExtractedFacts
    clean: dict  # SanitizedFacts
    draft: dict  # AnalysisDraft
    problems: list[str]  # figures the facts don't back
    tries: int  # analysis attempts so far
    next: str  # the supervisor's latest decision
    steps: Annotated[list[str], operator.add]  # who worked, in order
    decision: dict  # the person's decision at the pause


def decide(state: BrainState, max_tries: int) -> SupervisorDecision:
    """The order of trust: facts, then cleaning, then writing (with one retry), then finish."""
    if "facts" not in state:
        return SupervisorDecision(next="extraction", reason="No facts yet")
    if "clean" not in state:
        return SupervisorDecision(next="sanitization", reason="Facts not yet cleaned")
    if "draft" not in state:
        return SupervisorDecision(next="analysis", reason="Clean facts, no brief yet")
    if state.get("problems") and state.get("tries", 0) < max_tries:
        return SupervisorDecision(next="analysis", reason="Some figures are not backed")
    return SupervisorDecision(next="finish", reason="Brief ready for a person")


async def call_tool(tool: BaseTool, args: dict) -> Any:
    """An MCP tool's answer as Python data (the adapters return text or content blocks)."""
    result = await tool.ainvoke(args)
    if isinstance(result, list):
        result = "".join(block.get("text", "") for block in result if isinstance(block, dict))
    try:
        return json.loads(result)
    except (TypeError, ValueError):
        return result


def build_brain_graph(
    model: BaseChatModel, checkpointer: BaseCheckpointSaver | None = None
) -> CompiledStateGraph:
    writer = model.with_structured_output(AnalysisDraft)

    async def supervisor(state: BrainState, runtime: Runtime[BrainContext]) -> dict:
        decision = decide(state, runtime.context.max_analysis_tries)
        return {"next": decision.next, "steps": [f"supervisor: {decision.reason}"]}

    async def extraction(state: BrainState, runtime: Runtime[BrainContext]) -> dict:
        request = BrainRequest.model_validate(state["request"])
        tools = runtime.context.tools
        portfolio = await runtime.context.portfolio.positions(request.client_id)
        holdings = [Holding(**row) for row in portfolio["positions"]]
        sources = ["portfolio.positions"]
        if holdings and "get_quotes" in tools:  # prices from the market API over mTLS (Lab 74)
            quotes = await call_tool(
                tools["get_quotes"], {"tickers": [h.ticker for h in holdings][:10]}
            )
            prices = {q["ticker"]: q["price"] for q in quotes if isinstance(q, dict)}
            holdings = [h.model_copy(update={"price_usd": prices.get(h.ticker)}) for h in holdings]
            sources.append("mcp.market.get_quotes")
        notes: list[str] = []
        if "list_notes" in tools and "read_note" in tools:  # the desk's research notes (Lab 45)
            wanted = {h.sector.lower() for h in holdings} | {s.lower() for s in request.sectors}
            names = await call_tool(tools["list_notes"], {})
            matching = [name for name in names if any(word in name for word in wanted)]
            for name in matching[: runtime.context.max_notes]:
                text = await call_tool(tools["read_note"], {"name": name})
                notes.append(str(text)[:500])
            sources.append("mcp.notes")
        facts = ExtractedFacts(
            client_id=request.client_id,
            holdings=holdings,
            portfolio_value_usd=sum(h.market_value_usd for h in holdings),
            notes=notes,
            sources=sources,
        )
        return {"facts": facts.model_dump(), "steps": [f"extraction: {len(holdings)} holdings"]}

    async def sanitization(state: BrainState) -> dict:
        facts = ExtractedFacts.model_validate(state["facts"])
        safe = [note for note in facts.notes if not injection_rules(note)]  # Lab 71
        vault: dict[str, str] = {}
        masker = get_masker()
        masked = [masker.mask(note, vault) for note in safe]  # Lab 72
        clean = SanitizedFacts(
            facts=facts.model_copy(update={"notes": masked}),
            masked_values=len(vault),
            quarantined_notes=len(facts.notes) - len(safe),
        )
        note = f"sanitization: {clean.masked_values} masked, {clean.quarantined_notes} quarantined"
        return {"clean": clean.model_dump(), "steps": [note]}

    async def analysis(state: BrainState) -> dict:
        request = BrainRequest.model_validate(state["request"])
        clean = SanitizedFacts.model_validate(state["clean"])
        messages = [
            SystemMessage(ANALYST_PROMPT),
            HumanMessage(
                f"Question: {request.question}\n"
                f"Facts: {clean.facts.model_dump_json(exclude={'sources'})}"
            ),
        ]
        if state.get("problems"):
            messages.append(
                HumanMessage(f"These figures are not in the facts, fix them: {state['problems']}")
            )
        draft = await writer.ainvoke(messages)
        problems = [
            f"{f.label}: {f.value} {f.unit}" for f in unsupported_figures(draft, clean.facts)
        ]
        tries = state.get("tries", 0) + 1
        note = f"analysis: try {tries}, {len(problems)} unsupported figures"
        return {"draft": draft.model_dump(), "problems": problems, "tries": tries, "steps": [note]}

    async def approval(state: BrainState) -> dict:
        """The pause (Lab 62): the brief waits here until a person decides."""
        decision = interrupt({"draft": state["draft"], "problems": state.get("problems", [])})
        return {"decision": decision, "steps": [f"approval: {decision['action']}"]}

    graph = StateGraph(BrainState, context_schema=BrainContext)
    graph.add_node("supervisor", supervisor)
    graph.add_node("extraction", extraction)
    graph.add_node("sanitization", sanitization)
    graph.add_node("analysis", analysis)
    graph.add_node("approval", approval)
    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        lambda state: state["next"],
        {
            "extraction": "extraction",
            "sanitization": "sanitization",
            "analysis": "analysis",
            "finish": "approval",
        },
    )
    for agent in ("extraction", "sanitization", "analysis"):
        graph.add_edge(agent, "supervisor")
    graph.add_edge("approval", END)
    return graph.compile(name="brain", checkpointer=checkpointer)
