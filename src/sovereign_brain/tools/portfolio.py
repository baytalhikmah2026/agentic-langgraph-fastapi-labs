"""Portfolio tools for the research agent (Lab 22).

The model sees each tool's name, its parameters and the first line of its description,
and decides itself when to call it.
"""

from langchain_core.tools import BaseTool, tool

from sovereign_brain.services.portfolio import PortfolioService


def build_portfolio_tools(portfolio: PortfolioService) -> list[BaseTool]:
    @tool
    async def get_positions(client_id: str) -> dict:
        """List a client's holdings: ticker, name, sector and market value in US dollars."""
        return await portfolio.positions(client_id)

    @tool
    async def sector_exposure(client_id: str, sector: str) -> dict:
        """Share of a client's portfolio held in one sector, for example "Energy"."""
        return await portfolio.sector_exposure(client_id, sector)

    return [get_positions, sector_exposure]
