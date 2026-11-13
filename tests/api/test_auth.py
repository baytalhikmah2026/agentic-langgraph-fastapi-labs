from fastapi.testclient import TestClient


def test_login_returns_a_bearer_token(client: TestClient, password: str) -> None:
    response = client.post("/v1/auth/token", data={"username": "amina", "password": password})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 1800
    assert body["access_token"].count(".") == 2


def test_wrong_password_and_disabled_users_are_refused(client: TestClient, password: str) -> None:
    wrong = client.post("/v1/auth/token", data={"username": "amina", "password": "guess"})
    disabled = client.post(
        "/v1/auth/token", data={"username": "former.analyst", "password": password}
    )

    assert wrong.status_code == 401
    assert wrong.headers["WWW-Authenticate"] == "Bearer"
    assert disabled.status_code == 401
    assert disabled.json()["message"] == wrong.json()["message"]


def test_the_token_opens_protected_endpoints(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get("/v1/auth/me", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {"username": "amina", "full_name": "Amina Rahman", "role": "analyst"}


def test_research_without_a_token_is_401(client: TestClient) -> None:
    response = client.post(
        "/v1/research",
        json={"client_id": "C-1042", "question": "Summarise the exposure to energy stocks."},
    )

    assert response.status_code == 401
    assert response.json()["message"] == "Not authenticated"
