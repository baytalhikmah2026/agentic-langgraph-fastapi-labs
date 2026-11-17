"""The code-interpreter tool (Lab 47): the model writes Python, the sandbox runs it.

Two walls, one behind the other. First, Pydantic reads the code before it leaves the API and
refuses imports outside a short list, dangerous built-ins such as open() or eval(), and tricks
with double-underscore attributes. Second, whatever passes runs in the sandbox container,
which has no network, no secrets and nothing worth taking even if the first wall missed.
"""

import ast
from typing import Annotated

import httpx
from langchain_core.tools import tool
from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from sovereign_brain.core.settings import get_settings

ALLOWED_MODULES = frozenset(
    {"math", "statistics", "decimal", "fractions", "datetime", "json", "itertools", "collections"}
)
BLOCKED_NAMES = frozenset(
    {"open", "exec", "eval", "compile", "__import__", "input", "breakpoint", "globals", "locals",
     "vars", "getattr", "setattr", "delattr"}
)


def check_code(code: str) -> str:
    """Refuse code that is not Python, imports other modules or reaches for dangerous names."""
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        raise ValueError(f"not valid Python (line {error.lineno}): {error.msg}") from None
    for node in ast.walk(tree):
        modules = []
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules = [node.module or ""]
        for module in modules:
            if module.split(".")[0] not in ALLOWED_MODULES:
                allowed = ", ".join(sorted(ALLOWED_MODULES))
                raise ValueError(f"import of '{module}' is not allowed (allowed: {allowed})")
        if isinstance(node, ast.Name) and node.id in BLOCKED_NAMES:
            raise ValueError(f"'{node.id}' is not allowed in the sandbox")
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise ValueError("double-underscore attributes are not allowed in the sandbox")
    return code


class CodeRequest(BaseModel):
    """The model's code, checked before it is sent anywhere."""

    model_config = ConfigDict(extra="forbid")

    code: Annotated[
        str,
        Field(
            min_length=1,
            max_length=4000,
            description="Short Python 3.13 code that print()s its result. Only these imports: "
            "math, statistics, decimal, fractions, datetime, json, itertools, collections.",
        ),
        AfterValidator(check_code),
    ]


async def run_in_sandbox(
    code: str, url: str, transport: httpx.AsyncBaseTransport | None = None
) -> dict:
    """Send checked code to the sandbox runner and return its result."""
    async with httpx.AsyncClient(base_url=url, timeout=15.0, transport=transport) as client:
        response = await client.post("/run", json={"code": code})
    response.raise_for_status()
    return response.json()


@tool("run_python", args_schema=CodeRequest)
async def run_python(code: str) -> dict:
    """Run a short Python calculation in a locked sandbox and return what it printed."""
    return await run_in_sandbox(code, get_settings().sandbox_url)


SANDBOX_TOOLS = [run_python]
