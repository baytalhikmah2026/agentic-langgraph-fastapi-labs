"""Secrets from Vault (Lab 75): they replace the settings, and a missing one stops the start."""

import pytest

from sovereign_brain.core.settings import Settings
from sovereign_brain.core.vault import with_vault_secrets


def test_vault_values_replace_the_local_ones() -> None:
    settings = Settings(vault_addr="http://vault:8200")
    vault = {"jwt_secret": "from-vault-jwt", "market_api_token": "from-vault-market"}

    loaded = with_vault_secrets(settings, read=lambda _: vault)

    assert loaded.jwt_secret.get_secret_value() == "from-vault-jwt"
    assert loaded.market_api_token.get_secret_value() == "from-vault-market"
    assert "from-vault" not in repr(loaded)  # SecretStr keeps them out of logs


def test_a_missing_secret_stops_the_start() -> None:
    settings = Settings(vault_addr="http://vault:8200")

    with pytest.raises(RuntimeError, match="market_api_token"):
        with_vault_secrets(settings, read=lambda _: {"jwt_secret": "only-this-one"})
