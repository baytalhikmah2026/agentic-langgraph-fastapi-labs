"""The tool wall of the Research Desk (Labs 42, 47): every tool the analyst may use, in one list.

The graph binds these tools to the model and runs them in its tools station, and the API
lists them. One list means the model can never be offered a tool the graph cannot run.
"""

from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool

from sovereign_brain.tools.portfolio import PORTFOLIO_TOOLS
from sovereign_brain.tools.risk import RISK_TOOLS
from sovereign_brain.tools.sandbox import SANDBOX_TOOLS

RESEARCH_TOOLS: list[BaseTool] = [*PORTFOLIO_TOOLS, *RISK_TOOLS, *SANDBOX_TOOLS]


def wire_format(tool: BaseTool) -> dict:
    """The tool as the model receives it: the function-calling JSON that Ollama also accepts.

    Parameters that LangGraph fills in itself (such as `runtime`) are not part of it.
    """
    return convert_to_openai_tool(tool)
