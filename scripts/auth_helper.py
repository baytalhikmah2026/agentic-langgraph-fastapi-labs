"""Sign in to the running API from a script (Lab 16).

Lab 87: scripts can also reach the desk through the HTTPS ingress. Set SB_API_URL (for example
https://localhost:8443) and SB_API_CA_FILE (ops/certs/ca.crt, our own CA) before running them.
Lab 99: set SB_TOKEN_SCOPE (for example "research:run") to ask for a narrower sign-in.
"""

import getpass
import os
import ssl

import httpx

API_URL = os.environ.get("SB_API_URL", "http://127.0.0.1:8000")


def tls_verify() -> ssl.SSLContext | bool:
    """Trust our own CA when SB_API_CA_FILE names it; otherwise the usual public CAs."""
    ca_file = os.environ.get("SB_API_CA_FILE")
    return ssl.create_default_context(cafile=ca_file) if ca_file else True


def login(api: str, username: str) -> str:
    """Ask for the password, sign in, and return the access token."""
    password = getpass.getpass(f"Password for {username}: ")
    form = {"username": username, "password": password}
    if os.environ.get("SB_TOKEN_SCOPE"):  # Lab 99: only these scopes (space-separated)
        form["scope"] = os.environ["SB_TOKEN_SCOPE"]
    response = httpx.post(f"{api}/v1/auth/token", data=form, verify=tls_verify())
    response.raise_for_status()
    return response.json()["access_token"]
