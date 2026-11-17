"""The tool list endpoint (Labs 42, 44)."""

from fastapi.testclient import TestClient
from langchain_core.tools import StructuredTool


def test_the_api_lists_every_tool_with_its_form(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get("/v1/tools", headers=auth_headers)

    assert response.status_code == 200
    tools = {tool["name"]: tool for tool in response.json()}
    assert list(tools) == ["get_positions", "sector_exposure", "stress_test", "run_python"]
    assert "risk profile" in tools["stress_test"]["description"]
    assert "client_id" in tools["get_positions"]["parameters"]["properties"]


def test_the_tool_list_needs_a_token(client: TestClient) -> None:
    assert client.get("/v1/tools").status_code == 401


async def define(term: str) -> str:
    """A plain-words definition of a finance term."""
    return "A loan to a company or government."


def test_mcp_tools_are_listed_after_our_own(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    client.app.state.mcp_tools = [StructuredTool.from_function(coroutine=define, name="glossary")]

    tools = client.get("/v1/tools", headers=auth_headers).json()

    assert [(tool["name"], tool["source"]) for tool in tools] == [
        ("get_positions", "local"),
        ("sector_exposure", "local"),
        ("stress_test", "local"),
        ("run_python", "local"),
        ("glossary", "mcp"),
    ]
