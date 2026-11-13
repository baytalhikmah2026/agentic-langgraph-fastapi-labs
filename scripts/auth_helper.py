"""Sign in to the running API from a script (Lab 16)."""

import getpass

import httpx


def login(api: str, username: str) -> str:
    """Ask for the password, sign in, and return the access token."""
    password = getpass.getpass(f"Password for {username}: ")
    response = httpx.post(f"{api}/v1/auth/token", data={"username": username, "password": password})
    response.raise_for_status()
    return response.json()["access_token"]
