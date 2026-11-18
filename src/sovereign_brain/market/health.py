"""Health check of the market API over mutual TLS (Lab 74), used by Docker Compose."""

import urllib.request

from sovereign_brain.security.certs import client_context

if __name__ == "__main__":
    tls = client_context("/certs/ca.crt", "/certs/api-client.crt", "/certs/api-client.key")
    urllib.request.urlopen("https://localhost:8100/health", context=tls, timeout=3)
