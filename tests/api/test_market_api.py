"""The internal market-data API (Lab 46): prices for callers with the bearer token only."""

from fastapi.testclient import TestClient

from sovereign_brain.core.settings import get_settings
from sovereign_brain.market.app import app as market_app

market = TestClient(market_app)


def token_header() -> dict[str, str]:
    return {"Authorization": f"Bearer {get_settings().market_api_token.get_secret_value()}"}


def test_a_quote_with_the_token() -> None:
    response = market.get("/v1/quotes/glfp", headers=token_header())

    assert response.status_code == 200
    assert response.json() == {
        "ticker": "GLFP",
        "name": "Gulf Petroleum Co",
        "price": 62.4,
        "currency": "USD",
        "as_of": "2026-11-17",
    }


def test_no_token_no_price() -> None:
    assert market.get("/v1/quotes/GLFP").status_code == 401
    wrong = {"Authorization": "Bearer not-the-token"}
    assert market.get("/v1/quotes/GLFP", headers=wrong).status_code == 401


def test_an_unknown_ticker_is_404() -> None:
    assert market.get("/v1/quotes/ZZZZ", headers=token_header()).status_code == 404
