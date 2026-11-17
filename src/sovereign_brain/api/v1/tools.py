"""The tool wall, as the API shows it (Labs 42, 44): every tool the model may call, and its form."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from langchain_core.tools import BaseTool

from sovereign_brain.core.security import get_current_user
from sovereign_brain.schemas.tool import ToolInfo
from sovereign_brain.tools.registry import RESEARCH_TOOLS, wire_format

router = APIRouter(prefix="/v1/tools", tags=["tools"], dependencies=[Depends(get_current_user)])


def get_mcp_tools(request: Request) -> list[BaseTool]:
    """The tools discovered on MCP servers at start-up (Lab 44); empty when MCP is off."""
    return request.app.state.mcp_tools


def describe(tool: BaseTool, source: Literal["local", "mcp"]) -> ToolInfo:
    function = wire_format(tool)["function"]
    return ToolInfo(
        name=function["name"],
        description=function.get("description", ""),
        parameters=function["parameters"],
        source=source,
    )


@router.get("")
async def list_tools(
    mcp_tools: Annotated[list[BaseTool], Depends(get_mcp_tools)],
) -> list[ToolInfo]:
    """Every tool offered to the model: our own first, then those found on MCP servers."""
    return [describe(t, "local") for t in RESEARCH_TOOLS] + [describe(t, "mcp") for t in mcp_tools]
