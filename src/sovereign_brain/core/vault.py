"""Secrets from HashiCorp Vault (Lab 75): the API signs in to Vault and fetches them at start.

The API signs in with AppRole: a role ID (like a user name) and a secret ID (like a password),
both made for this one application. Vault answers with a short-lived token that may read only
the API's own secrets, and its audit log records every read.
"""

import logging
from collections.abc import Callable

import hvac
from pydantic import SecretStr

from sovereign_brain.core.settings import Settings

logger = logging.getLogger("sovereign_brain.vault")

VAULT_FIELDS = ("jwt_secret", "market_api_token", "approval_signing_key")  # Labs 75-76


def read_secrets(settings: Settings) -> dict[str, str]:
    """Sign in with AppRole and read the API's secrets (KV version 2, mount "secret")."""
    client = hvac.Client(url=settings.vault_addr, timeout=5)
    client.auth.approle.login(
        role_id=settings.vault_role_id, secret_id=settings.vault_secret_id.get_secret_value()
    )
    response = client.secrets.kv.v2.read_secret_version(
        path=settings.vault_secret_path, mount_point="secret", raise_on_deleted_version=True
    )
    return response["data"]["data"]


def with_vault_secrets(
    settings: Settings, read: Callable[[Settings], dict[str, str]] = read_secrets
) -> Settings:
    """A copy of the settings with the secrets from Vault; stops the start-up if one is missing."""
    found = read(settings)
    missing = [field for field in VAULT_FIELDS if not found.get(field)]
    if missing:
        raise RuntimeError(f"Vault has no value for: {', '.join(missing)}")
    logger.info("Secrets loaded from Vault: %s", ", ".join(VAULT_FIELDS))
    return settings.model_copy(update={field: SecretStr(found[field]) for field in VAULT_FIELDS})
