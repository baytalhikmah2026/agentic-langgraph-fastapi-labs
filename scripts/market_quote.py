"""Lab 74: ask the market API for one price over mutual TLS, from your own computer.

Usage: uv run python scripts/market_quote.py GLFP            (with the client certificate)
       uv run python scripts/market_quote.py GLFP --no-cert  (without it: refused)
"""

import ssl
import sys

import httpx

from sovereign_brain.core.settings import get_settings
from sovereign_brain.security.certs import client_context

CERTS = "ops/certs"


def main(ticker: str, with_cert: bool) -> None:
    if with_cert:
        tls = client_context(
            f"{CERTS}/ca.crt", f"{CERTS}/api-client.crt", f"{CERTS}/api-client.key"
        )
    else:
        tls = ssl.create_default_context(cafile=f"{CERTS}/ca.crt")  # trusts the server, no ID
    token = get_settings().market_api_token.get_secret_value()
    try:
        response = httpx.get(
            f"https://localhost:8100/v1/quotes/{ticker}",
            headers={"Authorization": f"Bearer {token}"},
            verify=tls,
            timeout=5.0,
        )
        print(response.status_code, response.text)
    except httpx.HTTPError as error:  # a refused handshake ends up here
        print(f"Refused: {error!r}")


if __name__ == "__main__":
    main(sys.argv[1], "--no-cert" not in sys.argv[2:])
