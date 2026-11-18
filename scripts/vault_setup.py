"""Lab 75: prepare Vault for the Research Desk (safe to run again).

1. switch on Vault's audit log (every request is written to /vault/logs/audit.log)
2. store the API's secrets, with new random values each time
3. a policy that may only read those secrets
4. an AppRole login for the API, with the role ID and secret ID from your .env

Usage: uv run python scripts/vault_setup.py   (Vault running, SB_VAULT_ROOT_TOKEN in .env)
"""

import secrets

import hvac
from hvac.exceptions import InvalidRequest

from sovereign_brain.core.settings import Settings

VAULT = "http://localhost:8200"
ROLE = "sovereign-brain-api"
POLICY = """
path "secret/data/sovereign-brain/*" {
  capabilities = ["read"]
}
"""


def main() -> None:
    settings = Settings()  # straight from .env: this script must not read from Vault itself
    client = hvac.Client(url=VAULT, token=settings.vault_root_token.get_secret_value())
    audit = client.sys.list_enabled_audit_devices()
    if "file/" not in audit.get("data", audit):
        client.sys.enable_audit_device("file", options={"file_path": "/vault/logs/audit.log"})
    client.secrets.kv.v2.create_or_update_secret(
        path=settings.vault_secret_path,
        mount_point="secret",
        secret={
            "jwt_secret": secrets.token_urlsafe(48),
            "market_api_token": secrets.token_urlsafe(32),
        },
    )
    client.sys.create_or_update_policy(name=ROLE, policy=POLICY)
    methods = client.sys.list_auth_methods()
    if "approle/" not in methods.get("data", methods):
        client.sys.enable_auth_method("approle")
    client.auth.approle.create_or_update_approle(
        ROLE, token_policies=[ROLE], token_ttl="1h", token_max_ttl="4h"
    )
    client.auth.approle.update_role_id(ROLE, settings.vault_role_id)
    try:
        secret_id = settings.vault_secret_id.get_secret_value()
        client.auth.approle.create_custom_secret_id(ROLE, secret_id)
    except InvalidRequest:  # already registered by an earlier run
        pass
    print(f"Vault ready: secrets at secret/{settings.vault_secret_path}, AppRole {ROLE}")


if __name__ == "__main__":
    main()
