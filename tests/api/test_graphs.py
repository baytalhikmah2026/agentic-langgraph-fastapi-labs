from fastapi.testclient import TestClient


def test_the_research_state_is_described(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get("/v1/graphs/research/state", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["graph"] == "research"
    assert body["nodes"] == ["intake", "classify", "analyse", "tools", "explain", "review"]
    assert body["fields"]["messages"] == "append (add_messages)"
    assert body["fields"]["trail"] == "append (add)"
    assert body["fields"]["status"] == "overwrite"


def test_the_state_description_needs_a_token(client: TestClient) -> None:
    response = client.get("/v1/graphs/research/state")

    assert response.status_code == 401


def test_the_graph_contract_is_published(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/v1/graphs/research/schema", headers=auth_headers)

    assert response.status_code == 200
    contract = response.json()
    assert sorted(contract["input"]["required"]) == ["client_id", "client_profile", "question"]
    assert sorted(contract["output"]["properties"]) == ["answer", "checked", "route"]
    assert sorted(contract["output"]["required"]) == ["answer", "route"]
