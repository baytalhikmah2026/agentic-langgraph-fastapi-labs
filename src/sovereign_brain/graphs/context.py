"""What every research run brings along (Lab 28): services and per-request settings.

The graph is built once; each run receives its own context. Nodes read it through
Runtime, tools through ToolRuntime. No global variables, nothing fixed at build time.
"""

from dataclasses import dataclass
from typing import Literal

from sovereign_brain.memory.semantic import SemanticMemory
from sovereign_brain.services.portfolio import PortfolioService


@dataclass(frozen=True)
class ResearchContext:
    portfolio: PortfolioService  # where the facts come from
    analyst: str  # who asked: written to the audit trail
    max_revisions: int = 2  # how often the review may send a draft back
    router: Literal["rules", "model"] = "rules"  # who chooses the track (Lab 30)
    memory: SemanticMemory | None = None  # long-term memory in Qdrant; None = off (Lab 38)
