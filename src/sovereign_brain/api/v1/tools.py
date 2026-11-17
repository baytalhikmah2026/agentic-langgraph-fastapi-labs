"""The tool wall, as the API shows it (Lab 42): which tools the model may call, and their forms."""

from fastapi import APIRouter, Depends

from sovereign_brain.core.security import get_current_user
from sovereign_brain.schemas.tool import ToolInfo
from sovereign_brain.tools.registry import RESEARCH_TOOLS, wire_format

router = APIRouter(prefix="/v1/tools", tags=["tools"], dependencies=[Depends(get_current_user)])


@router.get("")
async def list_tools() -> list[ToolInfo]:
    """Every tool offered to the model, with the description and parameters it reads."""
    tools = []
    for tool in RESEARCH_TOOLS:
        function = wire_format(tool)["function"]
        tools.append(
            ToolInfo(
                name=function["name"],
                description=function["description"],
                parameters=function["parameters"],
            )
        )
    return tools
