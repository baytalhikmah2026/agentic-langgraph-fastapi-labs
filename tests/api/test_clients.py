from fastapi.testclient import TestClient


def test_a_client_is_read_from_the_database(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get("/v1/clients/c-2077", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {
        "id": "C-2077",
        "name": "Northgate Logistics Ltd",
        "segment": "corporate",
        "risk_profile": "conservative",
    }


def test_an_unknown_client_is_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/v1/clients/C-9999", headers=auth_headers)

    assert response.status_code == 404
    assert response.json()["error"] == "not_found"
