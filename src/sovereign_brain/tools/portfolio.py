"""Portfolio tools for the research agent (Lab 22; runtime context since Lab 28).

The model sees each tool's name, its parameters and the first line of its description,
and decides itself when to call it. The `runtime` parameter is filled in by LangGraph
and is never shown to the model.
"""

from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime

from sovereign_brain.graphs.context import ResearchContext


@tool
async def get_positions(client_id: str, runtime: ToolRuntime[ResearchContext]) -> dict:
    """List a client's holdings: ticker, name, sector and market value in US dollars."""
    return await runtime.context.portfolio.positions(client_id)


@tool
async def sector_exposure(
    client_id: str, sector: str, runtime: ToolRuntime[ResearchContext]
) -> dict:
    """Share of a client's portfolio held in one sector, for example "Energy"."""
    return await runtime.context.portfolio.sector_exposure(client_id, sector)


PORTFOLIO_TOOLS = [get_positions, sector_exposure]
