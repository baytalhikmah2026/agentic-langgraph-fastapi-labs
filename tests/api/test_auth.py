from fastapi.testclient import TestClient

from sovereign_brain.core.security import hash_password
from sovereign_brain.db.models import User
from sovereign_brain.db.repository import UserRepository
from sovereign_brain.main import create_app

PASSWORD = "correct-horse-battery-42"
AMINA = User(
    username="amina",
    full_name="Amina Rahman",
    hashed_password=hash_password(PASSWORD),
    role="analyst",
    disabled=False,
)


class FakeUsers:
    async def get(self, username: str) -> User | None:
        return AMINA if username == AMINA.username else None


def make_client() -> TestClient:
    app = create_app()
    app.dependency_overrides[UserRepository] = FakeUsers
    return TestClient(app)


def test_login_returns_a_bearer_token() -> None:
    with make_client() as client:
        response = client.post("/v1/auth/token", data={"username": "amina", "password": PASSWORD})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 1800
    assert body["access_token"].count(".") == 2


def test_wrong_password_is_refused() -> None:
    with make_client() as client:
        response = client.post("/v1/auth/token", data={"username": "amina", "password": "guess"})

    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_the_token_opens_protected_endpoints() -> None:
    with make_client() as client:
        login = client.post("/v1/auth/token", data={"username": "amina", "password": PASSWORD})
        token = login.json()["access_token"]
        response = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {"username": "amina", "full_name": "Amina Rahman", "role": "analyst"}


def test_research_without_a_token_is_401() -> None:
    with make_client() as client:
        response = client.post(
            "/v1/research",
            json={"client_id": "C-1042", "question": "Summarise the exposure to energy stocks."},
        )

    assert response.status_code == 401
    assert response.json()["message"] == "Not authenticated"
