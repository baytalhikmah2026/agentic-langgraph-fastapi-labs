"""The tool list endpoint (Lab 42)."""

from fastapi.testclient import TestClient


def test_the_api_lists_every_tool_with_its_form(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get("/v1/tools", headers=auth_headers)

    assert response.status_code == 200
    tools = {tool["name"]: tool for tool in response.json()}
    assert list(tools) == ["get_positions", "sector_exposure", "stress_test"]
    assert "risk profile" in tools["stress_test"]["description"]
    assert "client_id" in tools["get_positions"]["parameters"]["properties"]


def test_the_tool_list_needs_a_token(client: TestClient) -> None:
    assert client.get("/v1/tools").status_code == 401
